# Быстрый старт

Установите пакет и оцените накопленный дефицит трассы по отсчётам.

```sh
pip install sydost-tracekit
```

Первый пример берёт синтетическую трассу (сценарий A, четыре ВМ), повторяет контроллер,
опрашиваемый раз в 4 секунды, и оценивает дефицит по отсчётам раз в 2 секунды:

```python
from sydost_tracekit import deficit_integral, estimate_from_samples, simulate, synthetic_trace

tr = synthetic_trace("A", T=600.0, dt=0.1, seed=7)  # эталонная трасса, шаг 0,1 с
run = simulate(tr, interval_s=4.0)  # выделение контроллера, опрашиваемого раз в 4 с
D = deficit_integral(tr.d, run.alloc, tr.dt)
est = estimate_from_samples(tr.t[::20], tr.d[:, ::20], run.alloc, tr.dt, "linear")
print(f"D = {D:.1f} MiB*s, линейная оценка по отсчётам раз в 2 с = {est:.1f} MiB*s")
```

Дальше:

- [Формат трасс](trace-format.md): как хранится потребность ВМ.
- [Границы](bounds.md): насколько велика погрешность оценки и какая частота опроса нужна.
- [Развёртывание регистратора](recorder-deployment.md): как запустить гостевой регистратор.
- [Командная строка](cli.md) и [API](api.md).

Примеры в [examples](../../examples/) показывают каждую функцию на коротком скрипте.
