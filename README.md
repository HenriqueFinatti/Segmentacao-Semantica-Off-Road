# Segmentação-Semantica-Off-Road

## Artigos
[Planilha de artigos do TCC](https://docs.google.com/spreadsheets/d/1R5qA6WePVfGyGWpKvlxbrkAxcpj4FcO8L0CS4ba1-YY/edit?usp=sharing)

## Estrutura de pastas
```
Segmentacao-Semantica-Off-Road/
|-- artigo/
|   |   ...
|-- data/
|   |-- dataset/
|   |   |-- test
|   |   |   |--  mask/
|   |   |   |--  new_segmentation/
|   |   |   |--  original/
|   |   |   |--  original_segmentation/
|   |   |-- train
|   |   |   |--  mask/
|   |   |   |--  new_segmentation/
|   |   |   |--  original/
|   |   |   |--  original_segmentation/
|   |-- raw/
|   |   |   ...
|-- results/
|   |-- deeplabv3+/
|   |   |-- images/
|   |   |   |   ...
|   |   |-- statistics/
|   |   |   |   ...  
|   |-- fcn/
|   |   |-- images/
|   |   |   |   ...
|   |   |-- statistics/
|   |   |   |   ...  
|-- scripst/
|   |-- files/
|   |   |   ...
|   |-- masks/
|   |   |   ...
|-- src/
|   |-- entities/
|   |   |   ...
|   |-- metrics/
|   |   |   ...
|-- .gitignore
|-- README.me
|-- requirements.txt
|-- settings.json
```