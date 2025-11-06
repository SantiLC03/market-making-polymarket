import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Cargar tus datos reales aquí
data = pd.read_csv('Data/query-results.csv')
data = data[data["SIDE"] == "Yes"]
