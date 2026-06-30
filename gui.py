import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import threading
import re
import logging
from typing import List
from core import StockAnalyzer

logger = logging.getLogger(__name__)

# ─── Paleta Dark Premium ───
BG_DARK = '#1a1b2e'
BG_CARD = '#232540'
BG_INPUT = '#2d2f52'
BG_HOVER = '#353760'
FG_PRIMARY = '#e8e9f3'
FG_SECONDARY = '#9395b0'
FG_DIM = '#6b6d8a'
ACCENT = '#6c63ff'
ACCENT_HOVER = '#857dff'
SUCCESS = '#4ade80'
WARNING = '#fbbf24'
DANGER = '#f87171'
BORDER = '#3a3c5e'
TREEVIEW_ALT = '#292b4a'


class ScrollableCheckboxFrame(tk.Frame):
    def __init__(self, parent, title, items, columns=6, **kw):
        kw.setdefault('bg', BG_CARD)
        super().__init__(parent, **kw)
        self.items = sorted(items)
        self.columns = columns
        self.check_vars = {}
        self.visible_items = self.items.copy()
        self._build(title)

    def _build(self, title):
        tk.Label(self, text=title, font=('Segoe UI', 10, 'bold'),
                 bg=BG_CARD, fg=ACCENT).grid(row=0, column=0, pady=5, sticky='w')

        sf = tk.Frame(self, bg=BG_CARD)
        sf.grid(row=1, column=0, sticky='ew', pady=4)
        tk.Label(sf, text='🔎', bg=BG_CARD, fg=FG_SECONDARY).pack(side='left', padx=(5,2))
        self.search_entry = tk.Entry(sf, font=('Segoe UI', 9), bg=BG_INPUT,
                                      fg=FG_PRIMARY, insertbackground=FG_PRIMARY,
                                      relief='flat', bd=0)
        self.search_entry.pack(side='left', fill='x', expand=True, padx=5, ipady=4)
        self.search_entry.bind('<KeyRelease>', self._filter)

        canvas = tk.Canvas(self, height=220, bg=BG_CARD, highlightthickness=0)
        sb = ttk.Scrollbar(self, orient='vertical', command=canvas.yview)
        self.inner = tk.Frame(canvas, bg=BG_CARD)
        self.inner.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0, 0), window=self.inner, anchor='nw')
        canvas.configure(yscrollcommand=sb.set)
        canvas.grid(row=2, column=0, sticky='nsew')
        sb.grid(row=2, column=1, sticky='ns')
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._create_cbs()

        cf = tk.Frame(self, bg=BG_CARD)
        cf.grid(row=3, column=0, sticky='ew', pady=5)
        for txt, cmd, clr in [
            ('✓ Todas', self.select_all, SUCCESS),
            ('✗ Nenhuma', self.deselect_all, DANGER),
            ('⇄ Inverter', self.invert, ACCENT)
        ]:
            b = tk.Label(cf, text=txt, font=('Segoe UI', 8, 'bold'), bg=clr,
                         fg='#111', padx=10, pady=3, cursor='hand2')
            b.pack(side='left', padx=4)
            b.bind('<Button-1>', lambda e, c=cmd: c())

    def _create_cbs(self):
        for w in self.inner.winfo_children():
            w.destroy()
        for i, item in enumerate(self.visible_items):
            if item not in self.check_vars:
                self.check_vars[item] = tk.BooleanVar(value=True)
            cb = tk.Checkbutton(self.inner, text=str(item), variable=self.check_vars[item],
                                font=('Segoe UI', 9), bg=BG_CARD, fg=FG_PRIMARY,
                                selectcolor=BG_INPUT, activebackground=BG_CARD,
                                activeforeground=FG_PRIMARY, anchor='w')
            cb.grid(row=i // self.columns, column=i % self.columns, sticky='w', padx=8, pady=1)

    def _filter(self, event=None):
        term = self.search_entry.get().lower()
        self.visible_items = [i for i in self.items if term in str(i)]
        self._create_cbs()

    def get_selected(self) -> List[int]:
        return [i for i, v in self.check_vars.items() if v.get()]

    def select_all(self):
        for i in self.visible_items: self.check_vars[i].set(True)

    def deselect_all(self):
        for i in self.visible_items: self.check_vars[i].set(False)

    def invert(self):
        for i in self.visible_items: self.check_vars[i].set(not self.check_vars[i].get())


class StockAnalyzerGUI:
    VERSION = '2.0'

    def __init__(self, root):
        self.root = root
        self.analyzer = StockAnalyzer()
        self.store_selector = None
        self._setup_styles()
        self._build_ui()
        self.root.after(200, self._auto_load)

    def _setup_styles(self):
        self.root.title(f'Analisador de Estoque v{self.VERSION}')
        self.root.geometry('1300x900')
        self.root.configure(bg=BG_DARK)
        self.root.minsize(900, 600)

        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Dark.TLabelframe', background=BG_CARD, foreground=ACCENT,
                         font=('Segoe UI', 10, 'bold'), borderwidth=0)
        style.configure('Dark.TLabelframe.Label', background=BG_CARD, foreground=ACCENT,
                         font=('Segoe UI', 10, 'bold'))
        style.configure('Treeview', background=BG_CARD, foreground=FG_PRIMARY,
                         fieldbackground=BG_CARD, font=('Segoe UI', 9), rowheight=26,
                         borderwidth=0)
        style.configure('Treeview.Heading', background=BG_INPUT, foreground=ACCENT,
                         font=('Segoe UI', 9, 'bold'), borderwidth=0)
        style.map('Treeview', background=[('selected', ACCENT)],
                  foreground=[('selected', '#fff')])
        style.configure('Horizontal.TProgressbar', troughcolor=BG_INPUT,
                         background=ACCENT, thickness=6)

    def _card(self, parent, text):
        f = tk.LabelFrame(parent, text=f'  {text}  ', font=('Segoe UI', 10, 'bold'),
                          bg=BG_CARD, fg=ACCENT, bd=1, relief='solid',
                          highlightbackground=BORDER, highlightthickness=1)
        return f

    def _btn(self, parent, text, cmd, bg=ACCENT, fg='#fff', **kw):
        b = tk.Label(parent, text=text, font=('Segoe UI', 10, 'bold'),
                     bg=bg, fg=fg, padx=16, pady=8, cursor='hand2', **kw)
        hover_bg = ACCENT_HOVER if bg == ACCENT else bg
        b.bind('<Enter>', lambda e: b.configure(bg=hover_bg))
        b.bind('<Leave>', lambda e: b.configure(bg=bg))
        b.bind('<Button-1>', lambda e: cmd())
        return b

    def _build_ui(self):
        # Header
        hdr = tk.Frame(self.root, bg=BG_DARK, height=50)
        hdr.pack(fill='x', padx=15, pady=(10, 5))
        tk.Label(hdr, text='📊 Analisador de Estoque', font=('Segoe UI', 16, 'bold'),
                 bg=BG_DARK, fg=FG_PRIMARY).pack(side='left')
        tk.Label(hdr, text=f'v{self.VERSION}', font=('Segoe UI', 10),
                 bg=BG_DARK, fg=FG_DIM).pack(side='left', padx=8, pady=4)

        # Main scrollable
        mf = tk.Frame(self.root, bg=BG_DARK)
        mf.pack(fill='both', expand=True, padx=10, pady=5)
        self.canvas = tk.Canvas(mf, bg=BG_DARK, highlightthickness=0)
        sb = ttk.Scrollbar(mf, orient='vertical', command=self.canvas.yview)
        self.sf = tk.Frame(self.canvas, bg=BG_DARK)
        self.sf.bind('<Configure>', lambda e: self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        self.canvas.create_window((0, 0), window=self.sf, anchor='nw')
        self.canvas.configure(yscrollcommand=sb.set)
        self.canvas.pack(side='left', fill='both', expand=True)
        sb.pack(side='right', fill='y')
        self.canvas.bind_all('<MouseWheel>', lambda e: self.canvas.yview_scroll(int(-1*(e.delta/120)), 'units'))

        self._build_code_input()
        self._build_store_selector()
        self._build_filters()
        self._build_results()

    def _build_code_input(self):
        card = self._card(self.sf, '📋 CÓDIGOS DOS PRODUTOS')
        card.pack(fill='x', padx=5, pady=5)
        tk.Label(card, text='Digite um código por linha. Suporte a regex: (regex:padrão)',
                 font=('Segoe UI', 8), bg=BG_CARD, fg=FG_DIM).pack(anchor='w', padx=10, pady=(5,0))
        self.code_text = scrolledtext.ScrolledText(
            card, height=6, font=('Consolas', 10), wrap='word',
            bg=BG_INPUT, fg=FG_PRIMARY, insertbackground=FG_PRIMARY,
            relief='flat', bd=0, selectbackground=ACCENT)
        self.code_text.pack(fill='x', padx=10, pady=8)

        bf = tk.Frame(card, bg=BG_CARD)
        bf.pack(fill='x', padx=10, pady=(0, 8))
        self._btn(bf, '🗑 Limpar', self._clear_codes, bg='#4a4c6e').pack(side='left', padx=2)
        self._btn(bf, '📂 Carregar Arquivo', self._load_from_file, bg='#4a4c6e').pack(side='left', padx=2)

    def _build_store_selector(self):
        self.store_card = self._card(self.sf, '🏪 SELEÇÃO DE LOJAS')
        self.store_card.pack(fill='both', padx=5, pady=5, expand=True)
        self.loading_label = tk.Label(self.store_card, text='⏳ Carregando lojas...',
                                       font=('Segoe UI', 10), bg=BG_CARD, fg=WARNING)
        self.loading_label.pack(pady=20)

    def _build_filter_row(self, parent, title, prefix):
        card = self._card(parent, title)
        card.pack(fill='x', padx=5, pady=3)
        enabled = tk.BooleanVar(value=(prefix == 'stock'))
        setattr(self, f'{prefix}_enabled', enabled)

        top = tk.Frame(card, bg=BG_CARD)
        top.pack(fill='x', padx=10, pady=5)
        cb = tk.Checkbutton(top, text='Ativar', variable=enabled,
                            font=('Segoe UI', 9), bg=BG_CARD, fg=FG_PRIMARY,
                            selectcolor=BG_INPUT, activebackground=BG_CARD)
        cb.pack(side='left')

        tk.Label(top, text='Condição:', bg=BG_CARD, fg=FG_SECONDARY,
                 font=('Segoe UI', 9)).pack(side='left', padx=(15, 5))
        op = ttk.Combobox(top, values=['menor_ou_igual','menor','maior_ou_igual','maior','entre'],
                          width=14, state='readonly', font=('Segoe UI', 9))
        op.set('menor_ou_igual')
        op.pack(side='left', padx=3)
        setattr(self, f'{prefix}_op', op)

        tk.Label(top, text='Valor:', bg=BG_CARD, fg=FG_SECONDARY,
                 font=('Segoe UI', 9)).pack(side='left', padx=(15, 5))
        v1 = tk.Entry(top, width=8, font=('Segoe UI', 9), bg=BG_INPUT, fg=FG_PRIMARY,
                      insertbackground=FG_PRIMARY, relief='flat', justify='center')
        v1.insert(0, '10' if prefix != 'ddv' else '5')
        v1.pack(side='left', padx=3, ipady=3)
        setattr(self, f'{prefix}_v1', v1)

        lbl2 = tk.Label(top, text='Valor 2:', bg=BG_CARD, fg=FG_SECONDARY, font=('Segoe UI', 9))
        v2 = tk.Entry(top, width=8, font=('Segoe UI', 9), bg=BG_INPUT, fg=FG_PRIMARY,
                      insertbackground=FG_PRIMARY, relief='flat', justify='center')
        setattr(self, f'{prefix}_v2_lbl', lbl2)
        setattr(self, f'{prefix}_v2', v2)

        def toggle_v2(evt=None):
            if op.get() == 'entre':
                lbl2.pack(side='left', padx=(10, 5))
                v2.pack(side='left', padx=3, ipady=3)
            else:
                lbl2.pack_forget()
                v2.pack_forget()
        op.bind('<<ComboboxSelected>>', toggle_v2)
        toggle_v2()

    def _build_filters(self):
        self._build_filter_row(self.sf, '📦 FILTRO DE ESTOQUE', 'stock')
        self._build_filter_row(self.sf, '📅 FILTRO DE DDV (DIAS DE VENDA)', 'ddv')
        self._build_filter_row(self.sf, '🏭 FILTRO ESTOQUE CD (70)', 'stock70')

    def _build_results(self):
        bf = tk.Frame(self.sf, bg=BG_DARK)
        bf.pack(fill='x', padx=5, pady=8)
        self.process_btn = self._btn(bf, '🔍  ANALISAR ESTOQUE', self._start_analysis,
                                      bg=ACCENT, fg='#fff')
        self.process_btn.pack(fill='x', ipady=4)

        self.export_btn = self._btn(bf, '📥  EXPORTAR CSV', self._export_csv, bg=SUCCESS, fg='#111')
        self.export_btn.pack(fill='x', ipady=2, pady=(5, 0))
        self.export_btn.configure(state='disabled')

        self.progress = ttk.Progressbar(self.sf, mode='indeterminate', length=400,
                                         style='Horizontal.TProgressbar')

        self.status_lbl = tk.Label(self.sf, text='Pronto para analisar',
                                    font=('Segoe UI', 9), bg=BG_DARK, fg=SUCCESS)
        self.status_lbl.pack(pady=4)

        rc = self._card(self.sf, '📊 RESULTADOS DA ANÁLISE')
        rc.pack(fill='both', expand=True, padx=5, pady=5)

        cols = ('Código', 'Descrição', 'Qtd Lojas', 'Lojas', 'Estoque Total', 'Média Venda', 'Estoque CD')
        self.tree = ttk.Treeview(rc, columns=cols, show='headings', height=18)
        widths = {'Código': 90, 'Descrição': 260, 'Qtd Lojas': 80, 'Lojas': 280,
                  'Estoque Total': 100, 'Média Venda': 100, 'Estoque CD': 100}
        for c in cols:
            self.tree.heading(c, text=c, command=lambda col=c: self._sort(col))
            anchor = 'w' if c in ('Descrição', 'Lojas') else 'center'
            self.tree.column(c, width=widths.get(c, 120), anchor=anchor)

        ts = ttk.Scrollbar(rc, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=ts.set)
        self.tree.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        ts.pack(side='right', fill='y', pady=5)

        self.tree.tag_configure('odd', background=TREEVIEW_ALT)
        self.tree.tag_configure('zero', foreground=DANGER)

        # Resumo
        self.summary_lbl = tk.Label(self.sf, text='', font=('Segoe UI', 9, 'bold'),
                                     bg=BG_DARK, fg=FG_SECONDARY)
        self.summary_lbl.pack(fill='x', padx=10, pady=5)
        self.filter_info = tk.Label(self.sf, text='', font=('Segoe UI', 8),
                                     bg=BG_DARK, fg=FG_DIM)
        self.filter_info.pack(fill='x', padx=10, pady=(0, 10))

    # ─── Actions ───

    def _auto_load(self):
        def load():
            df = self.analyzer.load_data()
            if df is not None:
                self.root.after(0, lambda: self._setup_stores(df))
            else:
                self.root.after(0, lambda: self._load_error())
        threading.Thread(target=load, daemon=True).start()

    def _load_error(self):
        self.loading_label.config(text='❌ Erro ao carregar. Clique para tentar novamente.', fg=DANGER)
        self.loading_label.config(cursor='hand2')
        self.loading_label.bind('<Button-1>', lambda e: self._auto_load())

    def _setup_stores(self, df):
        stores = sorted(df['Loja'].unique())
        self.loading_label.destroy()
        self.store_selector = ScrollableCheckboxFrame(
            self.store_card, f'LOJAS DISPONÍVEIS ({len(stores)})',
            stores, columns=6, bg=BG_CARD)
        self.store_selector.pack(fill='both', expand=True, padx=10, pady=8)
        self.status_lbl.config(text=f'✓ {len(df)} registros carregados | {len(stores)} lojas', fg=SUCCESS)

    def _clear_codes(self):
        self.code_text.delete('1.0', 'end')

    def _load_from_file(self):
        fp = filedialog.askopenfilename(filetypes=[('Text', '*.txt'), ('CSV', '*.csv')])
        if fp:
            try:
                with open(fp, 'r', encoding='utf-8') as f:
                    self._clear_codes()
                    self.code_text.insert('1.0', f.read().strip())
            except Exception as e:
                messagebox.showerror('Erro', str(e))

    def _get_val(self, entry, name):
        v = entry.get().strip().replace(',', '.')
        if not v:
            return None
        try:
            return float(v)
        except ValueError:
            raise ValueError(f'Valor inválido para {name}')

    def _get_filter(self, prefix):
        enabled = getattr(self, f'{prefix}_enabled')
        if not enabled.get():
            return None
        op = getattr(self, f'{prefix}_op').get()
        v1 = self._get_val(getattr(self, f'{prefix}_v1'), prefix)
        v2 = None
        if op == 'entre':
            v2 = self._get_val(getattr(self, f'{prefix}_v2'), prefix)
        if v1 is None:
            return None
        return (op, v1, v2)

    def _start_analysis(self):
        threading.Thread(target=self._run_analysis, daemon=True).start()

    def _run_analysis(self):
        try:
            self.root.after(0, lambda: self.process_btn.configure(bg=FG_DIM))
            self.root.after(0, lambda: self.progress.pack(pady=4))
            self.root.after(0, self.progress.start)
            self.root.after(0, lambda: self.status_lbl.config(text='⏳ Analisando...', fg=WARNING))

            text = self.code_text.get('1.0', 'end').strip()
            if not text:
                self.root.after(0, lambda: messagebox.showwarning('Aviso', 'Digite pelo menos um código.'))
                return

            codes = []
            for line in text.split('\n'):
                line = line.strip()
                if not line:
                    continue
                if line.startswith('regex:'):
                    try:
                        pat = re.compile(line[6:])
                        all_codes = self.analyzer.df['Código'].unique()
                        codes.extend([c for c in all_codes if pat.match(c)])
                    except re.error:
                        raise ValueError(f'Regex inválida: {line}')
                else:
                    codes.append(line)
            codes = list(dict.fromkeys(codes))  # dedup preserving order

            if not codes:
                self.root.after(0, lambda: messagebox.showwarning('Aviso', 'Nenhum código válido.'))
                return

            if not self.store_selector:
                self.root.after(0, lambda: messagebox.showerror('Erro', 'Lojas não carregadas.'))
                return

            stores = self.store_selector.get_selected()
            if not stores:
                self.root.after(0, lambda: messagebox.showwarning('Aviso', 'Selecione ao menos uma loja.'))
                return

            sf = self._get_filter('stock')
            df = self._get_filter('ddv')
            s7f = self._get_filter('stock70')

            results = self.analyzer.analyze(codes, stores, sf, df, s7f)

            self.root.after(0, lambda: self._show_results(results))
            self.root.after(0, lambda: self.export_btn.configure(state='normal'))
            self.root.after(0, lambda: self.status_lbl.config(
                text=f'✓ Análise concluída! {len(results)} produtos processados.', fg=SUCCESS))

        except ValueError as e:
            self.root.after(0, lambda: messagebox.showerror('Erro', str(e)))
        except Exception as e:
            logger.error(f'Erro: {e}')
            self.root.after(0, lambda: messagebox.showerror('Erro', str(e)))
        finally:
            self.root.after(0, self.progress.stop)
            self.root.after(0, self.progress.pack_forget)
            self.root.after(0, lambda: self.process_btn.configure(bg=ACCENT))

    def _show_results(self, results):
        for i in self.tree.get_children():
            self.tree.delete(i)

        total_stores = sum(r['Qtd Lojas'] for r in results)
        self.summary_lbl.config(
            text=f'📈 {len(results)} produtos | {total_stores} ocorrências em lojas')

        for idx, r in enumerate(results):
            tags = []
            if idx % 2: tags.append('odd')
            if r['Qtd Lojas'] == 0: tags.append('zero')
            self.tree.insert('', 'end', values=(
                r['Código'], r['Descrição'], r['Qtd Lojas'],
                r['Lojas'], r['Estoque Total'], r['Média Venda'], r['Estoque CD']
            ), tags=tuple(tags))

        self._update_filter_info()

    def _update_filter_info(self):
        parts = []
        op_map = {'menor_ou_igual':'≤','menor':'<','maior_ou_igual':'≥','maior':'>','entre':'entre'}
        for prefix, name in [('stock','Estoque'),('ddv','DDV'),('stock70','Est.CD')]:
            if getattr(self, f'{prefix}_enabled').get():
                op = op_map[getattr(self, f'{prefix}_op').get()]
                v1 = getattr(self, f'{prefix}_v1').get()
                if op == 'entre':
                    v2 = getattr(self, f'{prefix}_v2').get()
                    parts.append(f'{name} {op} {v1} e {v2}')
                else:
                    parts.append(f'{name} {op} {v1}')
        if self.store_selector:
            sel = len(self.store_selector.get_selected())
            tot = len(self.store_selector.check_vars)
            parts.append(f'Lojas: {sel}/{tot}')
        self.filter_info.config(text=' │ '.join(parts))

    def _export_csv(self):
        if not self.tree.get_children():
            messagebox.showwarning('Aviso', 'Nenhum resultado para exportar.')
            return
        fp = filedialog.asksaveasfilename(defaultextension='.csv',
                                           filetypes=[('CSV', '*.csv')])
        if not fp:
            return
        try:
            import pandas as pd
            cols = ('Código', 'Descrição', 'Qtd Lojas', 'Lojas', 'Estoque Total', 'Média Venda', 'Estoque CD')
            data = [self.tree.item(i)['values'] for i in self.tree.get_children()]
            pd.DataFrame(data, columns=cols).to_csv(fp, sep=';', decimal=',',
                                                      encoding='utf-8-sig', index=False)
            messagebox.showinfo('Sucesso', f'Exportado para {fp}')
        except Exception as e:
            messagebox.showerror('Erro', str(e))

    def _sort(self, col):
        items = [(self.tree.set(k, col), k) for k in self.tree.get_children('')]
        numeric_cols = ('Qtd Lojas', 'Estoque Total', 'Média Venda', 'Estoque CD')
        try:
            if col in numeric_cols:
                items.sort(key=lambda t: float(t[0]) if t[0] else 0, reverse=True)
            else:
                items.sort(key=lambda t: t[0].lower())
        except (ValueError, AttributeError):
            items.sort(key=lambda t: str(t[0]).lower())
        for idx, (_, k) in enumerate(items):
            self.tree.move(k, '', idx)
