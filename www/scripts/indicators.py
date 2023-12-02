# Función para calcular los pivotes de máximos y mínimos
def find_pivots(df, dev_threshold = 5.0):
    df['max_pivot'] = None
    df['min_pivot'] = None
    max_val = None
    min_val = None
    last = None

    for i in range(len(df)):
        high = df.at[i, 'high']
        low = df.at[i, 'low']

        if max_val is None or high > max_val:
            max_val = high
        if min_val is None or low < min_val:
            min_val = low

        if (max_val- high) / max_val * 100 >= dev_threshold:
            if last is None or last != 'max':
                df.at[i, 'max_pivot'] = max_val
            last = 'max'
            max_val = None
        elif (low - min_val) / min_val * 100 >= dev_threshold:
            if last is None or last != 'min':
                df.at[i, 'min_pivot'] = min_val
            min_val = None
            last = 'min'

    return df

def donchian(df, period = 20):
    df['dch_max'] = df['high'].rolling(window=period).max()
    df['dch_min'] = df['low'].rolling(window=period).min()
    df['dch_mean'] = (df['dch_max']+df['dch_min'])/2
    return df