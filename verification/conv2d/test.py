import torch
import torch.nn as nn
import numpy as np
import argparse
import torch.nn.functional as F

class BitQuant:
    def __init__(self, QuantType='4bitsym', WScale='PerTensor', quantscale=0.25):
        self.QuantType = QuantType
        self.WScale = WScale
        self.quantscale = quantscale
        if self.QuantType == '2bitsym':
            self.bpw = 2
        elif self.QuantType == '4bitsym':
            self.bpw = 4
        elif self.QuantType == '8bit':
            self.bpw = 8

    def activation_quant(self, x):
        if self.QuantType == '2bitsym':
            scale = 1.0 / x.abs().max(dim=-1, keepdim=True).values.clamp_(min=1e-5)
            y = (x * scale).round().clamp_(-2, 1)
        elif self.QuantType == '4bitsym':
            scale = 7.0 / x.abs().max(dim=-1, keepdim=True).values.clamp_(min=1e-5)
            y = (x * scale).round().clamp_(-8, 7)
        elif self.QuantType == '8bit':
            scale = 127.0 / x.abs().max(dim=-1, keepdim=True).values.clamp_(min=1e-5)
            y = (x * scale).round().clamp_(-128, 127)
        else:
            raise AssertionError(f"Invalid QuantType: {self.QuantType}. Expected one of: '2bitsym', '4bitsym', '8bit'")
        return y, scale

    def weight_quant(self, w):
        if self.WScale == 'PerOutput':
            mag = w.abs().max(dim=-1, keepdim=True)[0].clamp_(min=1e-5) / self.quantscale
        elif self.WScale == 'PerTensor':
            mag = w.abs().mean().clamp_(min=1e-5) / self.quantscale
        else:
            raise AssertionError(f"Invalid WScale: {self.WScale}. Expected one of: 'PerTensor', 'PerOutput'")

        scale = (2.0**(self.bpw-1)) / mag

        if self.QuantType == '2bitsym':
            u = ((w * scale - 0.5).round().clamp_(-2, 1) + 0.5)
        elif self.QuantType == '4bitsym':
            u = ((w * scale - 0.5).round().clamp_(-8, 7) + 0.5)
        elif self.QuantType == '8bit':
            u = (w * scale).round().clamp_(-128, 127)
        else:
            raise AssertionError(f"Invalid QuantType: {self.QuantType}. Expected one of: '2bitsym', '4bitsym', '8bit'")

        return u, scale, self.bpw

    def ste(self, x_q, x_scale, x): 
        """ 
        Applying STE for approximating gradients during backprop to avoid clipping  
        """
        return x + (x_q / x_scale - x).detach() 

    def norm(self, x):
        """Using only RMS"""
        y = torch.sqrt(torch.mean(x**2, dim=(-2,-1), keepdim=True))
        return x / y

    def dequantize_tensor(self, quantized_tensor, scale):
        if self.QuantType == '2bitsym':
            dequantized_tensor = (quantized_tensor + 0.5) / scale
        elif self.QuantType == '4bitsym':
            dequantized_tensor = (quantized_tensor + 0.5) / scale
        elif self.QuantType == '8bit':
            dequantized_tensor = quantized_tensor / scale
        else:
            raise AssertionError(f"Invalid QuantType: {self.QuantType}. Expected one of: '2bitsym', '4bitsym', '8bit'")
        return dequantized_tensor
    
class BitConv2d(nn.Conv2d, BitQuant):
    def __init__(self, in_channels, out_channels, kernel_size, stride, padding, groups=1,  QuantType='4bitsym', WScale='PerTensor', NormType='RMS', quantscale=0.25):
        nn.Conv2d.__init__(self,in_channels, out_channels, kernel_size=kernel_size, stride=stride, padding=padding, groups=groups, bias=False)
        BitQuant.__init__(self, QuantType, WScale, quantscale)

        self.NormType = NormType
        self.groups = groups
        self.stride = stride
        self.padding = padding

    def forward(self, x):
        w = self.weight 
        x_norm = self.norm(x)

        x_int, x_scale = self.activation_quant(x_norm)
        x_quant = self.ste(x_int, x_scale, x_norm)  

        w_int, w_scale, _ = self.weight_quant(w)
        w_quant = self.ste(w_int, w_scale, w)

        y = F.conv2d(x_quant, w_quant, groups=self.groups, stride=self.stride, padding=self.padding, bias=None)
        return y

    def get_weight(self): 
        w_int, w_scale, _ = self.weight_quant(self.weight)
        return self.ste(w_int, w_scale, self.weight)


def export_to_hfile(bpw, weights, weights_scale, filename):
    with open(filename, 'w') as f:
        f.write("#ifndef CONV_LAYER_H\n")
        f.write("#define CONV_LAYER_H\n\n")
        f.write("#include <stdint.h>\n\n")

        f.write(f"int8_t conv_weights[{weights.size}] = {{")
        f.write(", ".join(map(str, weights.flatten())))
        f.write("};\n\n")
        f.write(f"float conv_weights_scale = {weights_scale};\n\n")

        f.write(f"char* bpw = \"{bpw}\";\n")

        f.write("#endif // CONV_LAYER_H\n")

def save_tensor_custom(tensor, scale, filename):
    shape = tensor.shape
    with open(filename, 'wb') as f:
        for dim in shape:
            f.write(np.array(dim, dtype=np.int8).tobytes())
        f.write(scale.tobytes())
        f.write(tensor.tobytes())

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Training script') 
    parser.add_argument('--scale', type=float, default=0.25, help='Scaling for quantization')
    parser.add_argument('--bpw', type=str, default="8bit", help='Bits per weight')
    args = parser.parse_args()

    in_channels = 1
    mid_channels = 7
    kernel_size = 1
    conv_layer = BitConv2d(in_channels, mid_channels, kernel_size, stride=1, padding=0, QuantType=args.bpw, quantscale=args.scale)
    quant = BitQuant(QuantType=args.bpw, quantscale=args.scale)

    quant_weight, quant_weight_scale, _ = quant.weight_quant(conv_layer.weight.data)
    export_to_hfile(args.bpw, quant_weight.numpy(), quant_weight_scale.numpy(), "conv_layer.h")

    with torch.no_grad(): 
        input_tensor = torch.randn(1, 1, 12, 94)
        output_tensor = F.relu(conv_layer(input_tensor))

    input_tensor, input_scale = quant.activation_quant(input_tensor)
    output_tensor, output_scale = quant.activation_quant(output_tensor)

    save_tensor_custom(input_tensor.numpy(),input_scale.numpy(), "input_tensor.bin")
    save_tensor_custom(
        output_tensor.detach().numpy(), 
        output_scale.detach().numpy(), 
        "output_tensor.bin")


