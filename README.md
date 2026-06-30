# 📊 Analisador de Estoque v2.0

Ferramenta desktop para análise rápida de estoque a partir do arquivo `estoque99.csv` da rede.

## Funcionalidades

- **Análise por código**: Busque múltiplos códigos de produto simultaneamente
- **Filtros avançados**: Estoque, DDV (Dias de Venda) e Estoque CD (Loja 70)
- **Seleção de lojas**: Selecione/desmarque lojas individualmente com busca
- **Exportação CSV**: Exporte resultados filtrados para arquivo CSV
- **Suporte a regex**: Use `regex:padrão` para buscar códigos por expressão regular
- **Interface dark moderna**: Design premium com tema escuro

## Requisitos

- Python 3.10+
- pandas

## Instalação

```bash
pip install -r requirements.txt
```

## Uso

```bash
python analisadorestq.py
```

## Configuração

Crie um arquivo `config.ini` para apontar para o CSV da rede:

```ini
[DATA]
path = \\192.168.70.250\hd\csv\estoque99.csv
```

## Build (EXE)

```bash
pyinstaller --onefile --windowed --name AnalisadorEstoque --add-data "core.py;." --add-data "gui.py;." analisadorestq.py
```
