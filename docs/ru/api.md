# API

Публичные имена экспортируются из `sydost_tracekit`. У каждой функции есть docstring в стиле numpy
с исполняемыми примерами.

| Группа | Имена | Назначение |
|---|---|---|
| Трассы | `Trace`, `load_trace`, `save_trace`, `TraceFormatError` | трасса на равномерной сетке, формат CSV |
| Записи | `read_recorder_csv`, `demand`, `recordings_to_trace` | записи регистратора в трассы |
| Часы | `ClockSample`, `estimate_offset`, `guest_to_host`, `fit_drift` | совмещение хоста и гостя |
| Восстановление | `hold`, `linear` | отсчёты в функцию времени |
| Интеграл | `deficit`, `deficit_integral`, `total_variation`, `positive_part_integral`, `estimate_from_samples`, `sampling_study` | дефицит и его оценка |
| Границы | `hold_error_bound`, `hold_error_bounds_refined`, `linear_error_bound`, `estimate_constants`, `Constants`, `required_step`, `plan_sampling`, `Plan` | априорные и уточнённые границы, план опроса |
| Повтор | `ReserveController`, `simulate`, `RunResult` | повтор контроллера при постоянном опросе |
| Настройка | `sweep`, `pareto_front`, `select` | фронт «стоимость — качество» и выбор |
| Синтетика | `synthetic_trace`, `VmProfile`, `SCENARIOS` | сценарии A, B, C (совпадают с прототипом при том же зерне); D — контрольная |
| Гость | `sydost_tracekit.recorder.record`, `main` | регистратор на стандартной библиотеке (он же файл для гостей) |
| Хост | `sydost_tracekit.collector.collect`, `connect` | сборщик libvirt (дополнение `kvm`) |

Единицы: время в секундах, память в МиБ, накопленный дефицит в МиБ·с (командная строка выводит
ГиБ·с там, где это указано в названии).
