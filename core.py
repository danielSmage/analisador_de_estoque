import pandas as pd
import os
import hashlib
import logging
from typing import List, Dict, Optional
import configparser

logger = logging.getLogger(__name__)

class StockAnalyzer:
    """Motor de análise de estoque otimizado."""

    def __init__(self, config_file: str = 'config.ini'):
        self.df: Optional[pd.DataFrame] = None
        self._file_hash: Optional[str] = None
        self.data_path = self._load_config(config_file)
        self.USED_COLS = [
            'Código', 'Loja', 'Estoque', 'Media', 'DDV',
            'Descrição', 'Departamento', 'Categoria',
            'Fornecedor Principal', 'Aplicacao', 'Estoque Lojas',
            'DDV Lojas', 'PrCus', 'PrVen', 'UltEnt', 'UltSai'
        ]

    def _load_config(self, config_file: str) -> str:
        config = configparser.ConfigParser()
        default = r'\\192.168.70.250\hd\csv\estoque99.csv'
        if os.path.exists(config_file):
            config.read(config_file)
            return config.get('DATA', 'path', fallback=default)
        return default

    def _compute_hash(self, path: str) -> Optional[str]:
        try:
            h = hashlib.md5()
            with open(path, 'rb') as f:
                for chunk in iter(lambda: f.read(1 << 20), b''):
                    h.update(chunk)
            return h.hexdigest()
        except Exception:
            return None

    def load_data(self, force: bool = False) -> Optional[pd.DataFrame]:
        """Carrega CSV com cache por hash de arquivo."""
        try:
            new_hash = self._compute_hash(self.data_path)
            if not force and self.df is not None and new_hash == self._file_hash:
                logger.info("Dados em cache, reutilizando.")
                return self.df

            logger.info("Carregando dados do arquivo...")

            # Detectar colunas disponíveis
            sample = pd.read_csv(
                self.data_path, sep=';', quotechar='"',
                nrows=0, encoding='latin-1'
            )
            available = [c for c in self.USED_COLS if c in sample.columns]

            # Fallback para nomes com encoding diferente
            col_map = {}
            for sc in sample.columns:
                for uc in self.USED_COLS:
                    if uc not in available and sc.lower().replace('\x00', '') == uc.lower():
                        col_map[sc] = uc
                        available.append(sc)

            df = pd.read_csv(
                self.data_path, sep=';', quotechar='"', decimal=',',
                encoding='latin-1', low_memory=False,
                usecols=lambda c: c in available or c in col_map,
                dtype={'Código': str, 'Loja': 'Int32'}
            )

            if col_map:
                df.rename(columns=col_map, inplace=True)

            # Converter numéricos de forma vetorizada
            for col in ['Estoque', 'Media', 'DDV', 'Estoque Lojas', 'DDV Lojas', 'PrCus', 'PrVen']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

            # Limpar código
            if 'Código' in df.columns:
                df['Código'] = df['Código'].astype(str).str.strip()

            self.df = df
            self._file_hash = new_hash
            n_lojas = df['Loja'].nunique() if 'Loja' in df.columns else 0
            logger.info(f"Dados carregados: {len(df)} registros, {n_lojas} lojas")
            return df

        except Exception as e:
            logger.error(f"Erro ao carregar dados: {e}")
            return None

    def analyze(self, codes: List[str], stores: List[int],
                stock_filter=None, ddv_filter=None, stock70_filter=None) -> List[Dict]:
        """Análise vetorizada de estoque.
        
        Cada filtro é uma tupla (operador, val1, val2_ou_None).
        """
        if self.df is None:
            return []

        results = []
        df = self.df

        # Pré-filtrar por lojas selecionadas
        df_stores = df[df['Loja'].isin(stores)]

        # Pré-computar estoque 70 para todos os códigos de uma vez
        df_70 = df[df['Loja'] == 70].set_index('Código')

        # Pré-computar descrições
        desc_map = {}
        if 'Descrição' in df.columns:
            desc_series = df.drop_duplicates('Código').set_index('Código')
            if 'Descrição' in desc_series.columns:
                desc_map = desc_series['Descrição'].to_dict()

        for code in codes:
            estoque70 = 0
            if code in df_70.index:
                e70_data = df_70.loc[code]
                if isinstance(e70_data, pd.DataFrame):
                    estoque70 = e70_data['Estoque'].iloc[0]
                else:
                    estoque70 = e70_data['Estoque']
                estoque70 = float(estoque70)

            # Filtro de estoque 70
            if stock70_filter and not self._passes_filter(estoque70, *stock70_filter):
                continue

            code_df = df_stores[df_stores['Código'] == code]
            descricao = desc_map.get(code, '')

            if not code_df.empty:
                temp = code_df.copy()

                if stock_filter:
                    temp = self._apply_filter_df(temp, 'Estoque', *stock_filter)

                if ddv_filter:
                    temp = self._apply_filter_df(temp, 'DDV', *ddv_filter)

                stores_found = sorted(temp['Loja'].unique())
                media_total = round(temp['Media'].sum(), 2) if 'Media' in temp.columns else 0
                estoque_total = round(temp['Estoque'].sum(), 2) if not temp.empty else 0

                results.append({
                    'Código': code,
                    'Descrição': descricao,
                    'Qtd Lojas': len(stores_found),
                    'Lojas': self._format_stores(stores_found),
                    'Estoque Total': estoque_total,
                    'Média Venda': media_total,
                    'Estoque CD': estoque70
                })
            else:
                results.append({
                    'Código': code,
                    'Descrição': descricao,
                    'Qtd Lojas': 0,
                    'Lojas': '(Não encontrado)',
                    'Estoque Total': 0,
                    'Média Venda': 0,
                    'Estoque CD': estoque70
                })

        results.sort(key=lambda x: x['Qtd Lojas'], reverse=True)
        return results

    @staticmethod
    def _format_stores(stores: list) -> str:
        if not stores:
            return '(Nenhuma)'
        return ', '.join(str(s) for s in stores)

    @staticmethod
    def _passes_filter(value: float, op: str, v1: float, v2: Optional[float] = None) -> bool:
        if op == 'menor_ou_igual': return value <= v1
        if op == 'menor': return value < v1
        if op == 'maior_ou_igual': return value >= v1
        if op == 'maior': return value > v1
        if op == 'entre' and v2 is not None:
            lo, hi = min(v1, v2), max(v1, v2)
            return lo <= value <= hi
        return True

    @staticmethod
    def _apply_filter_df(df: pd.DataFrame, col: str, op: str, v1: float, v2=None) -> pd.DataFrame:
        if col not in df.columns:
            return df
        if op == 'menor_ou_igual': return df[df[col] <= v1]
        if op == 'menor': return df[df[col] < v1]
        if op == 'maior_ou_igual': return df[df[col] >= v1]
        if op == 'maior': return df[df[col] > v1]
        if op == 'entre' and v2 is not None:
            lo, hi = min(v1, v2), max(v1, v2)
            return df[(df[col] >= lo) & (df[col] <= hi)]
        return df
