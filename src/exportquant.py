# Taken from https://github.com/cpldcpu/BitNetMCU/blob/main/exportquant.py

import datetime
import numpy as np 

def export_to_hfile(quantized_model, filename, runname):
    """
    Exports the quantized model to an Ansi-C header file.

    Parameters:
    quantized_model (QuantizedModel): The quantized model to export.
    filename (str): The name of the header file to which the quantized model will be exported.
    runname (str): The name of the run for logging purposes.

    Note:
    This method supports multiple quantization types including 2bitsym, 4bitsym, and 8bit.
    """
    
    if not quantized_model.quantized_weights:
        raise ValueError("quantized_model has no quantized weights")

    # Determine maximum number of activations per layer (not implemented, placeholder)
    max_n_activations = 0  # Placeholder for maximum number of activations per layer

    with open(filename, 'w') as f:
        f.write(f'// Automatically generated header file\n')
        f.write(f'// Date: {datetime.now()}\n')
        f.write(f'// Quantized model exported from {runname}.pth\n')
        f.write('// Generated by exportquant.py\n\n')

        f.write('#include <stdint.h>\n\n')

        f.write('#ifndef BITNETMCU_MODEL_H\n')
        f.write('#define BITNETMCU_MODEL_H\n\n')

        f.write(f'// Number of layers\n')
        f.write(f'#define NUM_LAYERS {len(quantized_model.quantized_weights)}\n\n')
        f.write(f'// Maximum number of activations per layer\n')
        f.write(f'#define MAX_N_ACTIVATIONS {max_n_activations}\n\n')

        for name, (weights, scale) in quantized_model.quantized_weights.items():
            bpw = int(np.log2(weights.max() - weights.min() + 1))
            weights = weights.cpu().numpy()
            quantization_type = quantized_model.bit_quant.QuantType

            if (bpw * weights.size % 32) != 0:
                raise ValueError(f"Size mismatch: Weights must be packed to 32bit boundary. Weights size: {weights.size} Bit per weight: {bpw} Total bits: {bpw * weights.size}")

            print(f'Layer: {name} Quantization type: <{quantization_type}>, Bits per weight: {bpw}, Size: {weights.size}')

            data_type = np.uint32

            if quantization_type == '2bitsym':
                encoded_weights = ((weights < 0).astype(data_type) << 1) | (np.floor(np.abs(weights))).astype(data_type)
                QuantID = 2
            elif quantization_type == '4bitsym':
                encoded_weights = ((weights < 0).astype(data_type) << 3) | (np.floor(np.abs(weights))).astype(data_type)
                QuantID = 4
            elif quantization_type == '8bit':
                encoded_weights = np.floor(weights).astype(data_type)
                QuantID = 8
            else:
                print(f'Skipping layer {name} with quantization type {quantization_type} and {bpw} bits per weight. Quantization type not supported.')
                continue

            # Pack bits into 32 bit words
            weight_per_word = 32 // bpw 
            reshaped_array = encoded_weights.reshape(-1, weight_per_word)
            
            bit_positions = 32 - bpw - np.arange(weight_per_word, dtype=data_type) * bpw
            packed_weights = np.bitwise_or.reduce(reshaped_array << bit_positions, axis=1).view(data_type)
            
            # Write layer order, shape, shiftright and weights to the file
            f.write(f'// Layer: {name}\n')
            f.write(f'// QuantType: {quantization_type}\n')

            f.write(f'#define {name}_active\n')
            f.write(f'#define {name}_bitperweight {QuantID}\n')
            f.write(f'#define {name}_size {weights.size}\n')

            f.write(f'const uint32_t {name}_weights[] = {{')         
            for i, data in enumerate(packed_weights.flatten()):
                if i & 7 == 0:
                    f.write('\n\t')
                f.write(f'0x{data:08x},')
            f.write('\n}; //first channel is topmost bit\n\n')
           
        f.write('#endif\n')