"""Analisador de Estoque v2.0 - Entry Point"""
import logging
import tkinter as tk
from tkinter import messagebox

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    try:
        from gui import StockAnalyzerGUI
        root = tk.Tk()
        StockAnalyzerGUI(root)
        root.mainloop()
    except Exception as e:
        logging.critical(f"Erro crítico: {e}")
        messagebox.showerror("Erro Crítico", str(e))

if __name__ == '__main__':
    main()