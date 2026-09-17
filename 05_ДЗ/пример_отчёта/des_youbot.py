# -*- coding: utf-8 -*-
"""ДЭС-модель мобильного манипулятора youBot (вариант А) и синтез супервизора.

Расчётная часть к примеру отчёта по ДЗ. Реализует ровно то, что требуется
в задании: параллельную композицию, Ac/CoAc, проверку неблокируемости с
выдачей блокирующих состояний и трассы, синтез супремального управляемого
подъязыка (алгоритм 3.1 пособия), проверку неконфликтности модульных
супервизоров, наблюдатель.

Запуск:  python des_youbot.py            (печатает все результаты отчёта)
Зависимостей нет, Python 3.7+.
"""
from collections import deque
import json


class DES:
    """Детерминированный автомат-генератор G = (X, Σ, f, x0, Xm)."""

    def __init__(self, name, sigma, trans, x0, xm):
        self.name = name
        self.sigma = set(sigma)
        self.f = dict(trans)          # (x, σ) -> x'
        self.x0 = x0
        self.xm = set(xm)
        self.X = {x0} | {x for x, _ in self.f} | set(self.f.values())

    def active(self, x):
        return {e for (y, e) in self.f if y == x}


def parallel(*gs):
    """Параллельная композиция любого числа автоматов (только достижимая часть)."""
    sigma = set().union(*[g.sigma for g in gs])
    x0 = tuple(g.x0 for g in gs)
    trans = {}
    seen = {x0}
    q = deque([x0])
    while q:
        x = q.popleft()
        for e in sorted(sigma):
            nxt = []
            ok = True
            for g, xi in zip(gs, x):
                if e in g.sigma:
                    if (xi, e) not in g.f:
                        ok = False
                        break
                    nxt.append(g.f[(xi, e)])
                else:
                    nxt.append(xi)
            if not ok:
                continue
            y = tuple(nxt)
            trans[(x, e)] = y
            if y not in seen:
                seen.add(y)
                q.append(y)
    xm = {x for x in seen if all(xi in g.xm for g, xi in zip(gs, x))}
    return DES('||'.join(g.name for g in gs), sigma, trans, x0, xm), seen


def coaccessible(states, trans, xm):
    back = {}
    for (x, e), y in trans.items():
        if x in states and y in states:
            back.setdefault(y, set()).add(x)
    co = set(s for s in xm if s in states)
    q = deque(co)
    while q:
        y = q.popleft()
        for x in back.get(y, ()):
            if x not in co:
                co.add(x)
                q.append(x)
    return co


def accessible(states, trans, x0):
    if x0 not in states:
        return set()
    fw = {}
    for (x, e), y in trans.items():
        if x in states and y in states:
            fw.setdefault(x, set()).add(y)
    ac = {x0}
    q = deque([x0])
    while q:
        x = q.popleft()
        for y in fw.get(x, ()):
            if y not in ac:
                ac.add(y)
                q.append(y)
    return ac


def nonblocking(g, states):
    """(флаг, множество блокирующих состояний)."""
    co = coaccessible(states, g.f, g.xm)
    bad = states - co
    return (not bad), bad


def trace_to(g, target_set):
    """Кратчайшая трасса из x0 в любое состояние множества (поиск в ширину)."""
    prev = {g.x0: None}
    q = deque([g.x0])
    while q:
        x = q.popleft()
        if x in target_set:
            path = []
            while prev[x] is not None:
                x, e = prev[x]
                path.append(e)
            return list(reversed(path))
        for (y, e), z in sorted(g.f.items()):
            if y == x and z not in prev:
                prev[z] = (x, e)
                q.append(z)
    return None


def supcon(plant, specs, sigma_uc, verbose=False):
    """Супремальный управляемый и неблокирующий подъязык: алгоритм 3.1.

    H = G || E1 || ... || Ek; компонента 0 состояния H - состояние объекта G.
    Итерация: удалить состояния, где объект допускает неуправляемое событие,
    а H - нет (или оно ведёт в удалённое состояние); затем Trim; до неподвижной точки.
    Возвращает (состояния, H, журнал удалений по итерациям).
    """
    h, states = parallel(plant, *specs)
    h_states = set(states)
    log = []
    it = 0
    while True:
        it += 1
        bad_ctrl = set()
        for x in h_states:
            gx = x[0]
            for e in sigma_uc:
                if (gx, e) in plant.f:
                    y = h.f.get((x, e))
                    if y is None or y not in h_states:
                        bad_ctrl.add(x)
                        break
        h_states -= bad_ctrl
        co = coaccessible(h_states, h.f, h.xm)
        ac = accessible(co, h.f, h.x0)
        removed_block = h_states - ac
        new_states = ac
        log.append((it, len(bad_ctrl), len(removed_block), bad_ctrl))
        if new_states == h_states and not bad_ctrl:
            break
        h_states = new_states
        if not h_states:
            break
    return h_states, h, log


# ================================================================ модель объекта
UC = {'b_arrive', 'b_block', 'a_reached', 'a_stowed', 'g_ok', 'g_miss', 'g_slip',
      'v_detect', 'v_lost'}
UO = {'g_slip'}


def plant_components(with_giveup=True):
    # Платформа: H дом, T стол, B контейнер; m* - едет, s* - остановлена препятствием
    base = DES('Base',
               ['b_go_table', 'b_go_box', 'b_go_home', 'b_arrive', 'b_block', 'b_replan',
                'g_ok', 'g_put'],
               {('H', 'b_go_table'): 'mT', ('B', 'b_go_table'): 'mT',
                ('T', 'b_go_box'): 'mB', ('T', 'b_go_home'): 'mH', ('B', 'b_go_home'): 'mH',
                # уточнение позиции у стола после промаха захвата
                ('T', 'b_go_table'): 'mT',
                ('mT', 'b_arrive'): 'T', ('mB', 'b_arrive'): 'B', ('mH', 'b_arrive'): 'H',
                ('mT', 'b_block'): 'sT', ('mB', 'b_block'): 'sB', ('mH', 'b_block'): 'sH',
                ('sT', 'b_replan'): 'mT', ('sB', 'b_replan'): 'mB', ('sH', 'b_replan'): 'mH',
                # физическая связь: взять можно только у стола, положить - только у контейнера
                ('T', 'g_ok'): 'T', ('B', 'g_put'): 'B'},
               'H', ['H'])
    # Манипулятор: S транспортное положение, R выдвигается, X выдвинут, W складывается
    arm = DES('Arm',
              ['a_reach', 'a_reached', 'a_stow', 'a_stowed', 'g_ok', 'g_put'],
              {('S', 'a_reach'): 'R', ('R', 'a_reached'): 'X', ('X', 'a_stow'): 'W',
               ('W', 'a_stowed'): 'S', ('X', 'g_ok'): 'X', ('X', 'g_put'): 'X'},
              'S', ['S'])
    # Захват: O открыт, C закрывается, D держит
    grip = DES('Grip',
               ['g_close', 'g_ok', 'g_miss', 'g_put', 'g_slip'],
               {('O', 'g_close'): 'C', ('C', 'g_ok'): 'D', ('C', 'g_miss'): 'O',
                ('D', 'g_put'): 'O', ('D', 'g_slip'): 'O'},
               'O', ['O'])
    # Восприятие: Sr поиск, F предмет в поле зрения
    vis = DES('Vision', ['v_detect', 'v_lost'],
              {('Sr', 'v_detect'): 'F', ('F', 'v_lost'): 'Sr'}, 'Sr', ['Sr', 'F'])
    # Предмет: Tb на столе, Hn в захвате, Fl на полу, Bx в контейнере, Un помечен недоступным
    obj_t = {('Tb', 'g_ok'): 'Hn', ('Hn', 'g_slip'): 'Fl', ('Hn', 'g_put'): 'Bx'}
    obj_sigma = ['g_ok', 'g_slip', 'g_put']
    if with_giveup:
        obj_t[('Fl', 'o_giveup')] = 'Un'
        obj_sigma.append('o_giveup')
    obj = DES('Object', obj_sigma, obj_t, 'Tb', ['Bx', 'Un'])
    return base, arm, grip, vis, obj


# ================================================================ спецификации
GO = ['b_go_table', 'b_go_box', 'b_go_home']


def spec_motion():
    """E1 (R1): манипулятор не движется при движении платформы - и наоборот."""
    t = {}
    for e in GO:
        t[('Free', e)] = 'Base'
    t[('Base', 'b_arrive')] = 'Free'
    t[('Base', 'b_block')] = 'Base'
    t[('Base', 'b_replan')] = 'Base'
    for e in ('a_reach', 'a_stow'):
        t[('Free', e)] = 'Arm'
    for e in ('a_reached', 'a_stowed'):
        t[('Arm', e)] = 'Free'
    return DES('E1', GO + ['b_arrive', 'b_block', 'b_replan', 'a_reach', 'a_reached', 'a_stow', 'a_stowed'],
               t, 'Free', ['Free', 'Base', 'Arm'])


def spec_posture():
    """E2: платформа трогается только со сложенным манипулятором."""
    t = {('In', 'a_reach'): 'Out', ('Out', 'a_stowed'): 'In'}
    for e in GO:
        t[('In', e)] = 'In'
    return DES('E2', GO + ['a_reach', 'a_stowed'], t, 'In', ['In', 'Out'])


def spec_seen():
    """E3: захват закрывается только на видимом предмете."""
    return DES('E3', ['v_detect', 'v_lost', 'g_close'],
               {('N', 'v_detect'): 'Y', ('Y', 'v_lost'): 'N', ('Y', 'g_close'): 'Y'},
               'N', ['N', 'Y'])


def spec_no_drop():
    """E4 (R2 в жёсткой форме): предмет никогда не выпадает."""
    return DES('E4', ['g_slip'], {}, 'Ok', ['Ok'])


# ================================================================ наблюдатель
def observer(g, states, uo):
    def ur(S):
        S = set(S)
        q = deque(S)
        while q:
            x = q.popleft()
            for e in uo:
                y = g.f.get((x, e))
                if y is not None and y in states and y not in S:
                    S.add(y)
                    q.append(y)
        return frozenset(S)
    q0 = ur({g.x0})
    obs = {q0}
    dq = deque([q0])
    delta = {}
    so = g.sigma - uo
    while dq:
        qq = dq.popleft()
        for e in sorted(so):
            nxt = {g.f[(x, e)] for x in qq if (x, e) in g.f and g.f[(x, e)] in states}
            if not nxt:
                continue
            r = ur(nxt)
            delta[(qq, e)] = r
            if r not in obs:
                obs.add(r)
                dq.append(r)
    return q0, obs, delta


# ================================================================ отчёт
def spec_close_extended():
    """E5: захват закрывается только при выдвинутом манипуляторе."""
    return DES('E5', ['a_reached', 'a_stow', 'g_close'],
               {('Nx', 'a_reached'): 'Ex', ('Ex', 'a_stow'): 'Nx', ('Ex', 'g_close'): 'Ex'},
               'Nx', ['Nx', 'Ex'])


def spec_no_drop_moving():
    """E4': предмет не выпадает во время движения платформы (при стоящей - допустимо)."""
    t = {}
    for e in GO:
        t[('Still', e)] = 'Move'
    t[('Move', 'b_arrive')] = 'Still'
    t[('Move', 'b_block')] = 'Still'
    t[('Still', 'b_replan')] = 'Move'
    t[('Still', 'g_slip')] = 'Still'
    return DES("E4'", GO + ['b_arrive', 'b_block', 'b_replan', 'g_slip'], t, 'Still', ['Still', 'Move'])


def export_supervisor(sup, path):
    """Шаг 8 методики: супервизор как таблица переходов + таблица разрешений.

    Состояние супервизора - номер; для каждого номера хранятся переходы по всем
    событиям и список разрешённых управляемых событий. Исполнителю больше
    ничего не нужно: логики сверх таблиц в контроллере быть не должно.
    """
    states = sorted({sup.x0} | {x for x, _ in sup.f} | set(sup.f.values()), key=str)
    idx = {x: i for i, x in enumerate(states)}
    table = {'initial': idx[sup.x0], 'uncontrollable': sorted(UC), 'unobservable': sorted(UO),
             'states': []}
    for x in states:
        tr = {e: idx[y] for (z, e), y in sorted(sup.f.items()) if z == x}
        table['states'].append({
            'id': idx[x],
            'plant': list(x[0]),
            'marked': x in sup.xm,
            'next': tr,
            'enabled_controllable': sorted(e for e in tr if e not in UC),
        })
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(table, fh, ensure_ascii=False, indent=1)


def restrict(h, hs):
    """Автомат H, ограниченный множеством состояний супервизора."""
    t = {(x, e): y for (x, e), y in h.f.items() if x in hs and y in hs}
    return DES('S', h.sigma, t, h.x0, {x for x in h.xm if x in hs})


def main():
    out = {}
    print('=' * 72)
    print('1. Композиция объекта без события o_giveup')
    comps = plant_components(with_giveup=False)
    upper = 1
    for c in comps:
        upper *= len(c.X)
        print('   %-7s |X| = %d, |Σ| = %d' % (c.name, len(c.X), len(c.sigma)))
    g0, st0 = parallel(*comps)
    print('   верхняя оценка %d, достижимо %d, переходов %d' % (upper, len(st0), len(g0.f)))
    nb, bad = nonblocking(g0, st0)
    print('   неблокирующий: %s; блокирующих состояний: %d' % (nb, len(bad)))
    tr = trace_to(g0, bad)
    x = g0.x0
    for e in tr:
        x = g0.f[(x, e)]
    print('   кратчайшая трасса в блокировку: ' + ' '.join(tr))
    print('   состояние (Base, Arm, Grip, Vision, Object) = %s' % (x,))
    print('   предмет на полу во всех блокирующих состояниях: %s' % all(b[4] == 'Fl' for b in bad))
    out['v0'] = dict(upper=upper, reach=len(st0), trans=len(g0.f), blocking=len(bad), trace=tr, state=x)

    print('=' * 72)
    print('2. Объект с событием o_giveup (правило 6: отказ и его исход в модели)')
    comps = plant_components(with_giveup=True)
    g, st = parallel(*comps)
    nb, bad = nonblocking(g, st)
    print('   достижимо %d, переходов %d, неблокирующий: %s' % (len(st), len(g.f), nb))
    out['v1'] = dict(reach=len(st), trans=len(g.f), nonblocking=nb)

    print('=' * 72)
    print('3. Монолитный синтез по E1, E2, E3')
    specs = [spec_motion(), spec_posture(), spec_seen()]
    hs, h, log = supcon(g, specs, UC)
    hh, hall = parallel(g, *specs)
    print('   G||E1||E2||E3: достижимо %d; супервизор: %d состояний' % (len(hall), len(hs)))
    for it, nbad, nblk, _ in log:
        print('   итерация %d: удалено по управляемости %d, по блокировке/достижимости %d' % (it, nbad, nblk))
    sup = restrict(h, hs)
    disabled = {}
    for x in hs:
        for e in g.active(x[0]) - UC:
            y = h.f.get((x, e))
            if y is None or y not in hs:
                disabled[e] = disabled.get(e, 0) + 1
    print('   переходов супервизора %d' % len(sup.f))
    print('   запреты управляемых событий (число состояний, где событие физически возможно, но запрещено):')
    for e in sorted(disabled, key=lambda k: -disabled[k]):
        print('      %-11s %d' % (e, disabled[e]))
    delivered = trace_to(sup, {x for x in sup.xm if x[0][4] == 'Bx'})
    print('   кратчайшая успешная миссия под надзором (%d событий): %s' % (len(delivered), ' '.join(delivered)))
    def early_close(sup):
        """Разрешённые g_close при невыдвинутом манипуляторе."""
        return sorted({x[0] for (x, e) in sup.f if e == 'g_close' and x[0][1] != 'X'})
    ec = early_close(sup)
    print('   проверка разрешений: g_close разрешён при невыдвинутом манипуляторе в %d состояниях объекта,' % len(ec))
    ex = next((s for s in ec if s[4] == 'Tb' and s[1] == 'R'), ec[0])
    print('   например %s; трасса: %s' % (ex, ' '.join(trace_to(sup, {x for x in hs if x[0] == ex}) + ['g_close'])))
    out['mono'] = dict(h=len(hall), sup=len(hs), trans=len(sup.f), disabled=disabled, mission=delivered,
                       early_close=len(ec))

    print('-' * 72)
    print('3б. Спецификации пропускают закрытие захвата в воздухе. Добавляем E5 и повторяем')
    specs = [spec_motion(), spec_posture(), spec_seen(), spec_close_extended()]
    hs, h, log = supcon(g, specs, UC)
    sup = restrict(h, hs)
    print('   супервизор: %d состояний, %d переходов; ранних g_close: %d' % (len(hs), len(sup.f), len(early_close(sup))))
    delivered = trace_to(sup, {x for x in sup.xm if x[0][4] == 'Bx'})
    print('   кратчайшая успешная миссия (%d событий): %s' % (len(delivered), ' '.join(delivered)))
    nb, bad = nonblocking(sup, set(sup.X) & hs)
    print('   неблокирующий: %s' % nb)
    out['mono5'] = dict(sup=len(hs), trans=len(sup.f), mission=delivered)
    export_supervisor(sup, 'supervisor_youbot.json')
    print('   таблица супервизора записана в supervisor_youbot.json')

    print('=' * 72)
    print('4. Модульный синтез и неконфликтность')
    mods = []
    for sp in specs:
        s_i, h_i, _ = supcon(g, [sp], UC)
        mods.append((sp.name, s_i, h_i))
        print('   %s: %d состояний' % (sp.name, len(s_i)))
    x0 = (g.x0, tuple(m[2].x0 for m in mods))
    seen = {x0}
    q = deque([x0])
    ftr = {}
    while q:
        gx, hx = q.popleft()
        for e in sorted(g.active(gx)):
            nh = []
            ok = True
            for (name, s_i, h_i), hxi in zip(mods, hx):
                y = h_i.f.get((hxi, e))
                if y is None or y not in s_i:
                    ok = False
                    break
                nh.append(y)
            if not ok:
                continue
            nx = (g.f[(gx, e)], tuple(nh))
            ftr[((gx, hx), e)] = nx
            if nx not in seen:
                seen.add(nx)
                q.append(nx)
    xm = {x for x in seen if x[0] in g.xm and all(hxi in h_i.xm for (n, s_i, h_i), hxi in zip(mods, x[1]))}
    co = coaccessible(seen, ftr, xm)
    conflict = seen - co
    print('   совместная работа четырёх супервизоров: %d состояний, блокирующих %d -> %s' % (
        len(seen), len(conflict), 'неконфликтны' if not conflict else 'КОНФЛИКТ'))
    out['modular'] = dict(sizes=[(m[0], len(m[1])) for m in mods], prod=len(seen), conflict=len(conflict))

    print('=' * 72)
    print('5. Добавляем E4: «предмет никогда не выпадает»')
    hs4, h4, log4 = supcon(g, specs + [spec_no_drop()], UC)
    for it, nbad, nblk, badset in log4:
        kinds = sorted({(x[0][2], x[0][4]) for x in badset})
        print('   итерация %d: по управляемости %d, (захват, предмет) удалённых: %s; по блокировке %d' % (
            it, nbad, kinds, nblk))
    print('   супервизор: %d состояний' % len(hs4))
    out['nodrop'] = dict(sup=len(hs4), iters=[(a, b, c) for a, b, c, _ in log4])

    print('-' * 72)
    print("5б. Ослабленная E4': «не выпадает во время движения платформы»")
    hs5, h5, log5 = supcon(g, specs + [spec_no_drop_moving()], UC)
    for it, nbad, nblk, badset in log5:
        print('   итерация %d: по управляемости %d, по блокировке %d' % (it, nbad, nblk))
    sup5 = restrict(h5, hs5)
    bx = [x for x in sup5.xm if x[0][4] == 'Bx']
    un = [x for x in sup5.xm if x[0][4] == 'Un']
    print('   супервизор: %d состояний; маркированных с доставкой (Bx): %d, с отказом (Un): %d' % (
        len(hs5), len(bx), len(un)))
    moving_holding = [x for x in hs5 if x[0][2] == 'D' and x[0][0] in ('mT', 'mB', 'mH')]
    print('   состояний «едет с предметом в захвате» в супервизоре: %d' % len(moving_holding))
    out['nodrop_moving'] = dict(sup=len(hs5), marked_bx=len(bx), marked_un=len(un),
                                moving_holding=len(moving_holding), iters=[(a, b, c) for a, b, c, _ in log5])

    print('=' * 72)
    print('6. Наблюдатель при ненаблюдаемом g_slip (поведение под супервизором п. 3б)')
    q0, obs, delta = observer(sup, set(sup.X) & hs, UO)
    amb = [qq for qq in obs if {x[0][4] for x in qq} >= {'Hn', 'Fl'}]
    print('   состояний наблюдателя %d, из них с неоднозначностью «в захвате или на полу»: %d' % (len(obs), len(amb)))
    seq = ['v_detect', 'b_go_table', 'b_arrive', 'a_reach', 'a_reached', 'g_close', 'g_ok', 'a_stow',
           'a_stowed', 'b_go_box', 'b_arrive']
    cur = q0
    for e in seq:
        cur = delta.get((cur, e))
        if cur is None:
            print('   трасса недопустима на событии', e)
            break
    if cur is not None:
        objs = sorted({x[0][4] for x in cur})
        grips = sorted({x[0][2] for x in cur})
        print('   после «%s»:' % ' '.join(seq))
        print('      предмет ∈ %s, захват ∈ %s' % (objs, grips))
        out['observer'] = dict(obs=len(obs), amb=len(amb), estimate_obj=objs, estimate_grip=grips)
        nxt = sorted(e for (qq, e) in delta if qq == cur)
        print('      наблюдаемые события, возможные дальше: %s' % nxt)

    with open('des_youbot_results.json', 'w') as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1, default=list)


if __name__ == '__main__':
    main()
