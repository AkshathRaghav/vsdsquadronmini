

<div align="center">

# 🗣️🔥 QP-TinySpeech

*TinySpeech-Z <ins>Cuantizado</ins> de Bajo Bit para MCUs de bajo consumo*

</div>

# Visión general 

Este repositorio implementa la arquitectura TinySpeech basada en condensadores de atención, destinada a compensar la dependencia (y el costo computacional subsiguiente) de las capas de convolución dispersa. Esto reduce la cantidad de parámetros en órdenes de magnitud con respecto a intentos anteriores de reducido tamaño, manteniendo precisiones similares. También proporcionamos un motor de entrenamiento e inferencia para las familias Z, Y y X que alcanza una precisión superior al 91 %. Además, este proyecto contiene controladores para ejecutar el modelo en la placa VSDSquadron-Mini, que incorpora el microcontrolador CH32V003 y está equipada con solo 2 kb de SRAM | 16 kb de Flash.

<div align="center">
    <i> Artículo: https://arxiv.org/abs/2008.04245 | Código Oficial: </em>N/A</emm> </i>
</div>


# Resultados 

![image](https://github.com/user-attachments/assets/afde945d-5d28-41eb-8c2e-6781978e893c)

# Componentes Utilizados 

- [VSDSquadron Mini](https://www.vlsisystemdesign.com/vsdsquadronmini/)
- [ESP32 WROOM Moule](https://www.espressif.com/en/products/socs/esp32) 
- Varios (cables, batería, etc.)

# Experimentos 

Primero, instale los paquetes requeridos utilizando `pip install -r requirements.txt`. 

### Entrenamiento 

Puede entrenar la familia de modelos TinySpeech utilizando argumentos de CLI, o una de las configuraciones de experimento proporcionadas: 

```
python train.py --save_pth "models" --quant --quant_type 8 --model_type Z --epochs 50 --batch_size 64 --lr 0.01 --momentum 0.9 --seed 42 --device "cuda"

# O

python train.py --config tinyspeechz_google_speech.yaml
```

> Ofrecemos entrenamiento utilizando uno de `quant_mode = ["DQ", "SQ", "QAT", "UN"]`. Estos se expanden a **Cuantización Dinámica**, **Cuantización Estática**, **Entrenamiento Consciente de Cuantización (QAT)** y **Sin Cuantizar**.

### Inferencia 

Todas las capas necesarias para ejecutar el modelo se especifican en la carpeta `./verification`. Dentro de ella, encontrará subcarpetas para todas las capas con un archivo `.c` y un archivo `.py`. Primero, generamos un tensor y lo ejecutamos contra una capa/función de activación utilizada en `./training/tinyspeech.py` o `./training/modules.py`. Luego, guardamos esto en forma de binario `int8` o `float`, que posteriormente se carga en C para probar con el código personalizado. 

Puede probar todas las capas ejecutando `make verify_all` cuando se encuentre en el directorio raíz `./` del proyecto. 

# Observaciones

Ejecute `python -m torch.utils.bottleneck train.py --config <your_config_yaml>` para evaluar la eficiencia durante el entrenamiento. 

![image](https://github.com/user-attachments/assets/0e94ac50-ff67-4b37-b3a3-04274f8535f0)

Los condensadores de atención están diseñados para reemplazar o reducir la necesidad de capas convolucionales tradicionales, que suelen consumir muchos recursos. La idea es aprovechar un mecanismo de autoatención autónomo que pueda capturar y modelar de manera efectiva tanto las relaciones de activación locales como las entre canales dentro de los datos de entrada.

Por ahora, nos limitamos al entrenamiento consciente de cuantización para las variantes TinySpeech-Z y TinySpeech-M, considerando su tamaño reducido. En el Entrenamiento Consciente de Cuantización (QAT), los pesos del modelo no deben convertirse completamente a 4 bits durante todo el proceso de entrenamiento. En su lugar, los pesos deben permanecer en su formato de mayor precisión (típicamente fp32) durante el entrenamiento, pero simulados como de menor precisión (por ejemplo, 4 bits) durante las pasadas hacia adelante y hacia atrás. Este enfoque permite aprovechar los beneficios de la cuantización mientras se sigue utilizando la precisión de anchos de bit mayores para las actualizaciones de pesos.

# Agradecimientos 

- Nuestros módulos de entrenamiento consciente de cuantización fueron adaptados de [BitNetMCU: Redes Neuronales Cuantizadas de Bajo Bit y Alta Precisión en un Microcontrolador de Gama Baja](https://github.com/cpldcpu/BitNetMCU). Este proyecto, a su vez, se inspiró en su trabajo inicial sobre inferencia de CNN de 3 capas simples en un microcontrolador de gama baja. 

# Citación 

Si encuentra nuestro trabajo útil, por favor cítanos. 

```
@software{araviki-2024-qp_tinyspeech, 
    title="QP-TinySpeech: Extremely Low-Bit Quantized + Pruned TinySpeech-Z for low-power MCUs", 
    author="Ravikiran, Akshath Raghav"
    year={2024}
}
```

Artículo Original: 
```
@misc{wong-etal-2020-tinyspeech, 
    title="TinySpeech: Attention Condensers for Deep Speech Recognition Neural Networks on Edge Devices", 
    author="Wong, Alexander and 
            Famouri Mahmoud and 
            Pavlova Maya and 
            Surana Siddharth", 
    year={2020},
    eprint={2008.04245},
    archivePrefix={arXiv},
}
```
