import pandas as pd
from darts import TimeSeries
from darts.models import NBEATSModel

# Загрузка агрегированных данных (пример: ВВП + индекс соцнапряжения)
df = pd.read_csv("societal_metrics.csv", parse_dates=["date"])
series = TimeSeries.from_dataframe(df, "date", ["gdp", "tension_index"])

# Обучение
model = NBEATSModel(input_chunk_length=24, output_chunk_length=12)
model.fit(series, epochs=50)

# Прогноз на 60 периодов вперёд
forecast = model.predict(n=60)