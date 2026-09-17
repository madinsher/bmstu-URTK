"""Контроллер миссии youBot для примера отчёта по ДЗ (этапы 1-2).

Навыки решают, ЧТО делать; супервизор, синтезированный в des_youbot.py,
решает, ЧТО ЗАПРЕЩЕНО. Каждая команда проходит через sup.allowed(e),
каждый сигнал датчиков превращается в событие модели и передаётся в
sup.observe(e). Запретов сверх таблицы супервизора в этом файле нет.

Аргументы (controllerArgs мира), вида key=value:
  scenario = nominal | obstacle | miss | slip | hasty
  monitor  = 0 | 1   контроль зазора пальцев при перевозке (делает g_slip наблюдаемым)
  sup      = 0 | 1   работать ли через супервизор (0 - только для сравнения в сценарии hasty)
  seed     = N       случайное смещение предмета на столе (0 - без смещения)
  run      = имя     имя журнала
  record   = 0 | 1   видеозапись и снимки (нужен запуск с отрисовкой)

Результат: logs/<run>.csv (журнал событий) и logs/<run>.json (итог прогона).
Независимо от супервизора контроллер измеряет по физике сцены нарушения R1
(одновременное движение платформы и манипулятора) и проверяет, где на самом
деле оказался предмет.
"""
import csv
import json
import math
import os
import random
import sys

from controller import Supervisor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..', '..'))      # каталог пример_отчёта
sys.path.insert(0, ROOT)
from supervisor_runtime import Supervisor as DesSupervisor, SupervisorViolation  # noqa: E402

ARGS = dict(a.split('=', 1) for a in sys.argv[1:] if '=' in a)
SCENARIO = ARGS.get('scenario', 'nominal')
MONITOR = ARGS.get('monitor', '0') == '1'
USE_SUP = ARGS.get('sup', '1') == '1'
SEED = int(ARGS.get('seed', '0'))
RUN = ARGS.get('run', '%s_s%d' % (SCENARIO, SEED))
RECORD = ARGS.get('record', '0') == '1'
LOGDIR = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'logs')
os.makedirs(LOGDIR, exist_ok=True)

# ------------------------------------------------------------------ сцена и параметры
HOME = (-1.8, 0.0, 0.0)
TABLE_OBJ_NOMINAL = (0.4726, 0.0071)
GRASP_REACH = 0.4726                     # предмет перед роботом на этом расстоянии при захвате
BOX_POSE = (-0.6, -1.4, -math.pi / 2)    # поза платформы у контейнера
BOX_CENTER = (-0.6, -1.8)                # центр контейнера: предмет ложится в 0,40 м перед роботом
BOX_HALF = 0.10
V_MAX = 0.3                              # м/с
D_BLOCK = 0.35                           # м, порог препятствия
GAP_HELD = 0.0003
ARM_TOL = 0.03                           # рад, допуск достижения позы манипулятора                        # сумма положений пальцев: больше - предмет в захвате
T_MISSION = 300.0                        # с, требование R4

ARM_POSES = {
    'stow_empty': (0.0, 1.57, -2.635, 1.78, 0.0),
    'stow_held': (0.0, 0.678, 0.682, 1.74, 0.0),       # над задней площадкой (ARM_BACK_PLATE_HIGH)
    'table': (0.0, 0.0, -0.77, -1.21, 0.0),
    'floor': (0.0, -0.97, -1.55, -0.20, 0.0),          # предмет над самым полом
}

R = Supervisor()
DT = int(R.getBasicTimeStep())
random.seed(SEED)

arm_m = [R.getDevice('arm%d' % i) for i in range(1, 6)]
arm_s = [R.getDevice('arm%dsensor' % i) for i in range(1, 6)]
fing_m = [R.getDevice('finger::left'), R.getDevice('finger::right')]
fing_s = [R.getDevice('finger::leftsensor'), R.getDevice('finger::rightsensor')]
wheels = [R.getDevice('wheel%d' % i) for i in range(1, 5)]
gps = R.getDevice('gps')
imu = R.getDevice('inertial unit')
cam = R.getDevice('camera')
ds = [R.getDevice('ds_left'), R.getDevice('ds_right')]
for dev in arm_s + fing_s + ds + [gps, imu]:
    dev.enable(DT)
cam.enable(DT * 4)
cam.recognitionEnable(DT * 4)
for w in wheels:
    w.setPosition(float('inf'))
    w.setVelocity(0.0)
target = R.getFromDef('TARGET')

# ------------------------------------------------------------------ журнал и супервизор
log_rows = []
summary = {'run': RUN, 'scenario': SCENARIO, 'monitor': MONITOR, 'supervisor': USE_SUP, 'seed': SEED,
           'denied': 0, 'r1_violation_steps': 0, 'r1_violation_episodes': 0, 'events': 0, 'result': None}
sup = DesSupervisor(os.path.join(ROOT, 'supervisor_youbot.json'))
if MONITOR:
    sup.uo = set()          # зазор пальцев контролируется при перевозке: выпадение наблюдаемо
last_denied = [None]


def model_state():
    return '/'.join(sup.plant_state()) if USE_SUP else '-'


def log(kind, name, info=''):
    log_rows.append([round(R.getTime(), 3), kind, name, model_state(), info])
    print('%7.2f %-7s %-11s %-18s %s' % (R.getTime(), kind, name, model_state(), info), flush=True)


def event(e, info=''):
    """Событие от датчиков (неуправляемое либо подтверждение)."""
    summary['events'] += 1
    if USE_SUP:
        sup.observe(e)
    log('event', e, info)


def command(e, action, info=''):
    """Управляемое событие: действие выполняется, только если супервизор разрешает."""
    if USE_SUP and not sup.allowed(e):
        if last_denied[0] != e:            # считается и пишется в журнал первый отказ из серии
            summary['denied'] += 1
            log('denied', e, info)
        last_denied[0] = e
        return False
    last_denied[0] = None
    action()
    if USE_SUP:
        sup.observe(e)
    log('cmd', e, info)
    return True


# ------------------------------------------------------------------ примитивы
def pose2d():
    p = gps.getValues()
    return p[0], p[1], imu.getRollPitchYaw()[2]


def wrap(a):
    return math.atan2(math.sin(a), math.cos(a))


def set_wheels(vx, vy, w):
    lx, ly, rw = 0.228, 0.158, 0.05
    k = (lx + ly) * w
    for m, s in zip(wheels, (vx + vy + k, vx - vy - k, vx - vy + k, vx + vy - k)):
        m.setVelocity(s / rw)


def set_arm(name):
    for m, q in zip(arm_m, ARM_POSES[name]):
        m.setPosition(q)


def arm_error(name):
    return max(abs(s.getValue() - q) for s, q in zip(arm_s, ARM_POSES[name]))


settle = {'name': None, 'since': None, 'prev': None}


def arm_settled(name, hold=0.3):
    """Поза достигнута И звенья успокоились: ошибка < ARM_TOL и скорость < 0,02 рад/с
    на протяжении hold секунд. Одной ошибки положения мало - см. журнал нарушений R1."""
    q = [sv.getValue() for sv in arm_s]
    moving = settle['prev'] is not None and max(abs(a - b) for a, b in zip(q, settle['prev'])) / (DT / 1000.0) > 0.02
    settle['prev'] = q
    if arm_error(name) < ARM_TOL and not moving:
        if settle['name'] != name or settle['since'] is None:
            settle['name'], settle['since'] = name, R.getTime()
        return R.getTime() - settle['since'] >= hold
    settle['since'] = None
    return False


def set_gripper(opened):
    for m in fing_m:
        m.setPosition(0.025 if opened else 0.0)


def finger_gap():
    return fing_s[0].getValue() + fing_s[1].getValue()


def target_seen():
    return any(o.getModel() == 'target' for o in cam.getRecognitionObjects())


# ------------------------------------------------------------------ истина сцены (вне модели)
mon = {'arm': None, 'xy': None, 'both': False}


def physics_monitor():
    """R1 по физике сцены: платформа и манипулятор движутся одновременно."""
    q = [s.getValue() for s in arm_s[:4]]
    x, y, _ = pose2d()
    if mon['arm'] is not None:
        h = DT / 1000.0
        arm_speed = max(abs(a - b) for a, b in zip(q, mon['arm'])) / h
        base_speed = math.hypot(x - mon['xy'][0], y - mon['xy'][1]) / h
        both = arm_speed > 0.05 and base_speed > 0.02
        if both:
            summary['r1_violation_steps'] += 1
            if not mon['both']:
                summary['r1_violation_episodes'] += 1
                log('R1', 'нарушение', 'манипулятор %.2f рад/с, платформа %.2f м/с' % (arm_speed, base_speed))
        mon['both'] = both
    mon['arm'], mon['xy'] = q, (x, y)


shots_done = set()
VIEWS = {   # положение и ориентация камеры обзора для видео и снимков
    'overview': ([-3.0, 2.3, 2.7], [0.2539, 0.541, -0.8018, 1.0593]),
    'table': ([-0.75, 1.05, 1.05], [0.2051, 0.4637, -0.8619, 0.9483]),
    'box': ([-1.75, -0.55, 1.15], [0.2339, 0.6014, -0.764, 0.9419]),
}
SHOT_VIEW = {'start': 'overview', 'obstacle': 'overview', 'at_table': 'table', 'grasped': 'table',
             'slip': 'overview', 'at_box': 'box', 'placed': 'box', 'home': 'overview'}
viewpoint = R.getFromDef('VIEW')


def set_view(name):
    if RECORD and viewpoint is not None:
        pos, rot = VIEWS[name]
        viewpoint.getField('position').setSFVec3f(pos)
        viewpoint.getField('orientation').setSFRotation(rot)


def shot(name):
    if RECORD and name not in shots_done:
        shots_done.add(name)
        set_view(SHOT_VIEW.get(name, 'overview'))
        R.step(DT)
        R.exportImage(os.path.join(LOGDIR, '%s_%s.jpg' % (RUN, name)), 90)


timed_out = [False]
traj = {'last': -1.0, 'pts': []}         # t, x, y, yaw робота; x, y, z предмета


def step():
    if R.step(DT) == -1:
        raise SystemExit
    physics_monitor()
    t = R.getTime()
    if t - traj['last'] >= 0.1:
        traj['last'] = t
        x, y, yaw = pose2d()
        o = target.getPosition()
        traj['pts'].append([round(t, 2), round(x, 3), round(y, 3), round(yaw, 3), round(o[0], 3), round(o[1], 3), round(o[2], 3)])
    if R.getTime() > T_MISSION and not timed_out[0]:
        timed_out[0] = True
        raise TimeoutError


def wait(sec):
    for _ in range(int(sec * 1000 / DT)):
        step()


def wait_until(cond, timeout):
    t0 = R.getTime()
    while not cond():
        step()
        if R.getTime() - t0 > timeout:
            return False
    return True


def issue(e, action, info='', poll=None):
    """Выдать команду; пока она запрещена, продолжать опрос датчиков (poll)."""
    while not command(e, action, info):
        if poll:
            poll()
        step()


# ------------------------------------------------------------------ отказы, вносимые в сцену
injected = {'slip': False, 'miss': False}


def inject_slip():
    injected['slip'] = True
    x, y, yaw = pose2d()
    target.getField('translation').setSFVec3f([x + 0.35 * math.cos(yaw + 1.3), y + 0.35 * math.sin(yaw + 1.3), 0.02])
    target.resetPhysics()
    log('inject', 'g_slip', 'предмет выпал из захвата')
    shot('slip')


MISS_SHIFT = float(ARGS.get('shift', '0.06'))   # м, смещение предмета после подъезда


def inject_miss():
    injected['miss'] = True
    p = target.getPosition()
    target.getField('translation').setSFVec3f([p[0], p[1] + MISS_SHIFT, p[2]])
    target.resetPhysics()
    log('inject', 'shift', 'предмет смещён на %d мм после подъезда' % round(MISS_SHIFT * 1000))


# ------------------------------------------------------------------ навыки
def arm_to(name, cmd_event, info=''):
    issue(cmd_event, lambda: set_arm(name), info)
    if not wait_until(lambda: arm_settled(name), 8.0):
        errs = ', '.join('%.3f' % (sv.getValue() - q) for sv, q in zip(arm_s, ARM_POSES[name]))
        log('fault', 'arm_timeout', 'поза %s не достигнута, ошибки звеньев: %s' % (name, errs))
        raise RuntimeError('arm_timeout')
    event('a_reached' if cmd_event == 'a_reach' else 'a_stowed')


def navigate(goal, go_event, already_issued=False, carrying=False):
    """NavigateTo: движение к позе, остановка и объезд при препятствии."""
    if not already_issued:
        issue(go_event, lambda: None, 'к (%.2f, %.2f)' % goal[:2])
    set_view('overview')
    waypoints = [goal]
    replanned = False
    while True:
        gx, gy, gyaw = waypoints[0]
        final = len(waypoints) == 1
        x, y, yaw = pose2d()
        dx, dy = gx - x, gy - y
        dist = math.hypot(dx, dy)
        eyaw = wrap(gyaw - yaw)
        if not final and dist < 0.08:
            waypoints.pop(0)
            continue
        if final and dist < 0.01 and abs(eyaw) < 0.02:
            set_wheels(0, 0, 0)
            wait(0.3)
            event('b_arrive', 'ошибка позы %.3f м' % dist)
            return
        near = min(d.getValue() for d in ds)
        forward = (dx * math.cos(yaw) + dy * math.sin(yaw)) > 0.3 * dist   # датчики смотрят вперёд
        if not replanned and forward and near < D_BLOCK and math.hypot(goal[0] - x, goal[1] - y) > 0.7:
            set_wheels(0, 0, 0)
            event('b_block', 'препятствие в %.2f м' % near)
            shot('obstacle')
            wait(0.5)
            d1 = (x - 0.7 * math.sin(yaw), y + 0.7 * math.cos(yaw), gyaw)
            d2 = (d1[0] + 1.0 * math.cos(yaw), d1[1] + 1.0 * math.sin(yaw), gyaw)
            waypoints = [d1, d2, goal]
            replanned = True
            issue('b_replan', lambda: None, 'объезд через (%.2f, %.2f)' % d1[:2])
            continue
        vx_w, vy_w = 1.5 * dx, 1.5 * dy
        sp = math.hypot(vx_w, vy_w)
        if sp > V_MAX:
            vx_w, vy_w = vx_w * V_MAX / sp, vy_w * V_MAX / sp
        set_wheels(vx_w * math.cos(yaw) + vy_w * math.sin(yaw),
                   -vx_w * math.sin(yaw) + vy_w * math.cos(yaw),
                   max(-0.8, min(0.8, 2.0 * eyaw)))
        step()
        if carrying:
            if SCENARIO == 'slip' and not injected['slip'] and math.hypot(goal[0] - x, goal[1] - y) < 0.9:
                inject_slip()
            if MONITOR and USE_SUP and sup.plant_state()[2] == 'D' and finger_gap() < GAP_HELD:
                event('g_slip', 'зазор пальцев %.4f: предмета в захвате нет' % finger_gap())


def table_pose():
    """Поза у стола по положению предмета. Истина сцены здесь играет роль
    идеальной системы распознавания: пример не про точность СТЗ."""
    o = target.getPosition()
    return (o[0] - GRASP_REACH, o[1], 0.0)


def mission():
    set_arm('stow_empty')
    set_gripper(False)
    wait_until(lambda: arm_settled('stow_empty'), 10.0)
    wait(0.5)
    if RECORD:
        R.movieStartRecording(os.path.join(LOGDIR, RUN + '.mp4'), 1280, 720, 0, 90, 1, False)
    shot('start')
    if wait_until(target_seen, 3.0):
        event('v_detect', 'предмет распознан камерой')

    attempts = 0
    while True:
        navigate(table_pose(), 'b_go_table')
        shot('at_table')
        if SCENARIO == 'miss' and not injected['miss']:
            inject_miss()
        if USE_SUP and sup.plant_state()[3] == 'Sr':
            if not wait_until(target_seen, 5.0):
                summary['result'] = 'not_detected'
                return
            event('v_detect', 'предмет распознан у стола')
        set_gripper(True)
        arm_to('table', 'a_reach', 'над столом')
        issue('g_close', lambda: set_gripper(False))
        wait(1.5)
        if finger_gap() > GAP_HELD:
            event('g_ok', 'зазор пальцев %.4f' % finger_gap())
            shot('grasped')
            break
        event('g_miss', 'зазор пальцев %.4f: промах' % finger_gap())
        attempts += 1
        arm_to('stow_empty', 'a_stow')
        if attempts > 2:
            summary['result'] = 'grasp_failed'
            return

    if SCENARIO == 'hasty':
        # поспешная политика: сразу после команды сложить манипулятор - команда ехать
        issue('a_stow', lambda: set_arm('stow_held'), 'с предметом')

        def poll_stowed():
            if sup.plant_state()[1] == 'W' and arm_settled('stow_held'):
                event('a_stowed')
        issue('b_go_box', lambda: None, 'поспешно, не дожидаясь a_stowed', poll=poll_stowed if USE_SUP else None)
        navigate(BOX_POSE, 'b_go_box', already_issued=True, carrying=True)
        if USE_SUP is False or sup.plant_state()[1] == 'W':
            wait_until(lambda: arm_settled('stow_held'), 8.0)
            event('a_stowed')
    else:
        arm_to('stow_held', 'a_stow', 'с предметом')
        navigate(BOX_POSE, 'b_go_box', carrying=True)
    shot('at_box')

    if USE_SUP and sup.plant_state()[2] == 'O':      # выпадение наблюдалось
        issue('o_giveup', lambda: None, 'предмет помечен недоступным')
        result = 'gave_up'
    else:
        arm_to('floor', 'a_reach', 'над контейнером')
        issue('g_put', lambda: set_gripper(True))
        wait(1.0)
        shot('placed')
        arm_to('stow_empty', 'a_stow')
        result = 'delivered'
    navigate(HOME, 'b_go_home')
    shot('home')
    summary['result'] = result


def finish():
    ox, oy = target.getPosition()[:2]
    in_box = abs(ox - BOX_CENTER[0]) < BOX_HALF and abs(oy - BOX_CENTER[1]) < BOX_HALF
    summary.update({
        'time_s': round(R.getTime(), 2),
        'object_xy': [round(ox, 3), round(oy, 3)],
        'object_in_box': in_box,
        'model_object': sup.plant_state()[4] if USE_SUP else None,
        'model_marked': sup.states[sup.state]['marked'] if USE_SUP else None,
    })
    # ложный успех: по модели предмет уложен, а в контейнере его нет
    summary['false_success'] = bool(summary['result'] == 'delivered' and not in_box)
    with open(os.path.join(LOGDIR, RUN + '.csv'), 'w', newline='', encoding='utf-8') as fh:
        wr = csv.writer(fh)
        wr.writerow(['t', 'kind', 'name', 'model_state', 'info'])
        wr.writerows(log_rows)
    with open(os.path.join(LOGDIR, RUN + '_traj.json'), 'w', encoding='utf-8') as fh:
        json.dump(traj['pts'], fh)
    with open(os.path.join(LOGDIR, RUN + '.json'), 'w', encoding='utf-8') as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=1)
    print('SUMMARY', json.dumps(summary, ensure_ascii=False), flush=True)


if SEED:
    p = target.getPosition()
    target.getField('translation').setSFVec3f([TABLE_OBJ_NOMINAL[0] + random.uniform(-0.03, 0.03),
                                               TABLE_OBJ_NOMINAL[1] + random.uniform(-0.12, 0.12), p[2]])
    target.resetPhysics()

try:
    mission()
except TimeoutError:
    summary['result'] = 'timeout'
except SupervisorViolation as exc:
    summary['result'] = 'model_violation'
    log('ERROR', 'модель', str(exc))
except RuntimeError as exc:
    summary['result'] = str(exc)
set_wheels(0, 0, 0)
wait(1.0)
finish()
if RECORD:
    R.movieStopRecording()
    while not R.movieIsReady():
        R.step(DT)
R.simulationQuit(0)
