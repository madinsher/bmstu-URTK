# -*- coding: utf-8 -*-
"""Иллюстрации к примеру отчёта: автоматы, архитектура, расчёты, результаты испытаний.

  python gen_figs.py            схемы и расчётные графики
  python gen_figs.py logs       графики по журналам Webots (каталог ../webots/logs)

Нужен matplotlib. Все рисунки - в этом каталоге.
"""
import glob
import json
import math
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch, Rectangle

plt.rcParams['font.family'] = 'DejaVu Sans'
HERE = os.path.dirname(os.path.abspath(__file__))
LOGS = os.path.join(HERE, '..', 'webots', 'logs')

NAVY, AMB, GREEN, RED, GREY, BG = '#1E2761', '#D97706', '#2C7A5A', '#B85042', '#5A6478', '#F4F7FC'
BLUE = '#2F6DB5'


# ------------------------------------------------------------------ примитивы
def canvas(w, h, title=None):
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_xlim(0, w)
    ax.set_ylim(0, h)
    ax.axis('off')
    if title:
        ax.text(w / 2, h - 0.2, title, ha='center', va='top', fontsize=14, weight='bold', color=NAVY)
    return fig, ax


def save(fig, name):
    fig.savefig(os.path.join(HERE, name), dpi=130, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(name)


def state(ax, x, y, name, r=0.32, init=False, marked=False, fc='white', ec=NAVY, fs=11, init_dir=(-1, 0)):
    ax.add_patch(Circle((x, y), r, facecolor=fc, edgecolor=ec, lw=1.6, zorder=3))
    if marked:
        ax.add_patch(Circle((x, y), r - 0.05, facecolor='none', edgecolor=ec, lw=1.1, zorder=3))
    ax.text(x, y, name, ha='center', va='center', fontsize=fs, weight='bold', zorder=4)
    if init:
        dx, dy = init_dir
        ax.add_patch(FancyArrowPatch((x + dx * (r + 0.45), y + dy * (r + 0.45)), (x + dx * (r + 0.03), y + dy * (r + 0.03)),
                                     arrowstyle='-|>', mutation_scale=12, color=NAVY, lw=1.5))


def edge(ax, p, q, lab, r=0.32, rad=0.0, color=NAVY, fs=9.5, off=0.2, lpos=0.5, ls='-'):
    (px, py), (qx, qy) = p, q
    d = math.hypot(qx - px, qy - py)
    ux, uy = (qx - px) / d, (qy - py) / d
    a = (px + ux * r, py + uy * r)
    b = (qx - ux * r, qy - uy * r)
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle='-|>', mutation_scale=12, color=color, lw=1.4,
                                 connectionstyle='arc3,rad=%s' % rad, linestyle=ls, zorder=2))
    mx, my = a[0] + (b[0] - a[0]) * lpos, a[1] + (b[1] - a[1]) * lpos
    rnx, rny = uy, -ux                      # правая нормаль: в эту сторону изгибает arc3 при rad > 0
    if rad:
        sgn = 1 if rad > 0 else -1
        bulge = 4 * lpos * (1 - lpos) * 0.5 * rad * d
        lx, ly = mx + rnx * (bulge + sgn * abs(off)), my + rny * (bulge + sgn * abs(off))
    else:
        lx, ly = mx - rnx * off, my - rny * off
    ax.text(lx, ly, lab, ha='center', va='center', fontsize=fs, color=color, style='italic',
            bbox=dict(facecolor='white', edgecolor='none', pad=0.5, alpha=0.85), zorder=5)


def loop(ax, x, y, lab, r=0.32, up=True, color=NAVY, fs=9.5):
    s = 1 if up else -1
    ax.add_patch(FancyArrowPatch((x - 0.15, y + s * r * 0.9), (x + 0.15, y + s * r * 0.9), arrowstyle='-|>',
                                 mutation_scale=10, color=color, lw=1.3, connectionstyle='arc3,rad=%s' % (-s * 2.4)))
    ax.text(x, y + s * (r + 0.5), lab, ha='center', va='center', fontsize=fs, color=color, style='italic')


def block(ax, x, y, w, h, text, fc=BG, ec=NAVY, fs=10.5, bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.02,rounding_size=0.08', facecolor=fc,
                                edgecolor=ec, lw=1.5))
    ax.text(x + w / 2, y + h / 2, text, ha='center', va='center', fontsize=fs, weight='bold' if bold else 'normal',
            linespacing=1.35)


def arrow(ax, p, q, color=NAVY, lw=1.6, rad=0.0, ls='-'):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle='-|>', mutation_scale=13, color=color, lw=lw,
                                 connectionstyle='arc3,rad=%s' % rad, linestyle=ls))


# ------------------------------------------------------------------ 1. платформа
def fig_base():
    fig, ax = canvas(12.4, 7.3, 'Автомат платформы G_B: 9 состояний')
    H, mT, T, mB, B, mH = (1.3, 3.5), (4.6, 5.4), (8.4, 5.4), (10.6, 3.5), (8.4, 1.6), (4.6, 1.6)
    sT, sB, sH = (4.6, 6.55), (11.85, 3.5), (4.6, 0.45)
    state(ax, *H, 'H', marked=True, init=True, fc='#DCF0E6', ec=GREEN)
    for p, n in ((T, 'T'), (B, 'B')):
        state(ax, *p, n, fc='#DCE6F7')
    for p, n in ((mT, 'mT'), (mB, 'mB'), (mH, 'mH')):
        state(ax, *p, n, fs=10)
    for p, n in ((sT, 'sT'), (sB, 'sB'), (sH, 'sH')):
        state(ax, *p, n, fs=9.5, fc='#F5DEDB', ec=RED, r=0.28)
    edge(ax, H, mT, 'b_go_table', off=0.3)
    edge(ax, mT, T, 'b_arrive', color=GREY, off=0.25)
    edge(ax, T, mB, 'b_go_box', off=0.35)
    edge(ax, mB, B, 'b_arrive', color=GREY, off=0.35)
    edge(ax, B, mH, 'b_go_home', off=0.25)
    edge(ax, mH, H, 'b_arrive', color=GREY, off=0.3)
    edge(ax, B, mT, 'b_go_table', lpos=0.25, off=0.28)
    edge(ax, T, mH, 'b_go_home', lpos=0.25, off=-0.28)
    edge(ax, mT, sT, 'b_block', color=RED, rad=0.5, off=0.15, r=0.3)
    edge(ax, sT, mT, 'b_replan', rad=0.5, off=0.15, r=0.3)
    edge(ax, mB, sB, 'b_block', color=RED, rad=0.5, off=0.15, r=0.3, fs=8.5)
    edge(ax, sB, mB, 'b_replan', rad=0.5, off=0.15, r=0.3, fs=8.5)
    edge(ax, mH, sH, 'b_block', color=RED, rad=0.5, off=0.15, r=0.3)
    edge(ax, sH, mH, 'b_replan', rad=0.5, off=0.15, r=0.3)
    loop(ax, T[0], T[1], 'b_go_table: уточнение позиции после промаха', up=True)
    ax.text(0.2, 6.7, 'H - база, T - у стола, B - у контейнера;\nm* - едет, s* - остановлена препятствием',
            fontsize=9.5, color=GREY, ha='left', va='top')
    ax.text(8.9, 0.1, 'петли g_ok в T и g_put в B: взять можно только у стола,\nположить - только у контейнера;\nсерые подписи - неуправляемые события',
            fontsize=9.5, color=GREY, ha='left', va='bottom')
    save(fig, 'fig_01_platform.png')


# ------------------------------------------------------------------ 2. манипулятор, захват, восприятие, предмет
def fig_components():
    fig, ax = canvas(12.0, 8.0, 'Автоматы манипулятора, захвата, восприятия и предмета')
    # манипулятор
    ax.text(0.3, 6.9, 'Манипулятор G_A', fontsize=12, weight='bold', color=NAVY)
    S, Rr, X, W = (1.0, 5.4), (3.2, 5.4), (5.4, 5.4), (3.2, 4.2)
    state(ax, *S, 'S', init=True, marked=True, init_dir=(0, 1))
    state(ax, *Rr, 'R')
    state(ax, *X, 'X')
    state(ax, *W, 'W')
    edge(ax, S, Rr, 'a_reach')
    edge(ax, Rr, X, 'a_reached', color=GREY)
    edge(ax, X, W, 'a_stow', off=-0.3)
    edge(ax, W, S, 'a_stowed', color=GREY, off=-0.3)
    loop(ax, X[0], X[1], 'g_ok, g_put')
    # захват
    ax.text(6.6, 6.9, 'Захват G_G', fontsize=12, weight='bold', color=NAVY)
    O, C, D = (7.3, 5.4), (9.3, 5.4), (11.3, 5.4)
    state(ax, *O, 'O', init=True, marked=True, init_dir=(0, 1))
    state(ax, *C, 'C')
    state(ax, *D, 'D')
    edge(ax, O, C, 'g_close', rad=-0.25, off=0.15)
    edge(ax, C, O, 'g_miss', color=GREY, rad=-0.25, off=0.15)
    edge(ax, C, D, 'g_ok', color=GREY)
    edge(ax, D, O, 'g_put', rad=0.45, off=0.1, lpos=0.5)
    edge(ax, D, O, 'g_slip (без контроля зазора не наблюдается)', color=RED, rad=0.75, off=0.25, ls='--')
    # восприятие
    ax.text(0.3, 2.9, 'Восприятие G_V', fontsize=12, weight='bold', color=NAVY)
    Sr, F = (1.2, 1.5), (3.8, 1.5)
    state(ax, *Sr, 'Sr', init=True, marked=True, init_dir=(0, 1))
    state(ax, *F, 'F', marked=True)
    edge(ax, Sr, F, 'v_detect', color=GREY, rad=-0.3, off=0.1)
    edge(ax, F, Sr, 'v_lost', color=GREY, rad=-0.3, off=0.1)
    # предмет
    ax.text(5.4, 2.9, 'Предмет G_O', fontsize=12, weight='bold', color=NAVY)
    Tb, Hn, Bx, Fl, Un = (6.0, 1.6), (8.2, 1.6), (10.6, 2.3), (10.6, 0.8), (11.6, 0.8)
    Un = (11.7, 0.1 + 0.7)
    state(ax, *Tb, 'Tb', init=True, init_dir=(0, 1))
    state(ax, *Hn, 'Hn')
    state(ax, *Bx, 'Bx', marked=True, fc='#DCF0E6', ec=GREEN)
    Fl = (9.6, 0.5)
    Un = (11.4, 0.5)
    state(ax, *Fl, 'Fl', fc='#F5DEDB', ec=RED)
    state(ax, *Un, 'Un', marked=True, fc='#FFE9C7', ec=AMB)
    edge(ax, Tb, Hn, 'g_ok', color=GREY)
    edge(ax, Hn, Bx, 'g_put')
    edge(ax, Hn, Fl, 'g_slip', color=RED, off=-0.3)
    edge(ax, Fl, Un, 'o_giveup', off=0.25)
    ax.text(5.4, -0.25, 'Un добавлено после первой проверки: без него «предмет на полу» - блокировка',
            fontsize=9, color=GREY, ha='left')
    save(fig, 'fig_02_components.png')


# ------------------------------------------------------------------ 3. спецификации
def fig_specs():
    fig, ax = canvas(12.0, 6.6, 'Спецификации E1, E2, E3, E5 (каждая - над своим подалфавитом)')
    ax.text(0.3, 5.9, 'E1 (R1): движется кто-то один', fontsize=11, weight='bold', color=NAVY)
    Fr, Bs, Ar = (3.0, 4.5), (0.9, 4.5), (5.1, 4.5)
    state(ax, *Fr, 'Free', init=True, marked=True, init_dir=(0, 1), fs=9.5, r=0.36)
    state(ax, *Bs, 'Base', fs=9.5, r=0.36)
    state(ax, *Ar, 'Arm', fs=9.5, r=0.36)
    edge(ax, Fr, Bs, 'b_go_*', r=0.36, rad=-0.35, off=0.1)
    edge(ax, Bs, Fr, 'b_arrive', r=0.36, rad=-0.35, off=0.1, color=GREY)
    edge(ax, Fr, Ar, 'a_reach, a_stow', r=0.36, rad=0.35, off=-0.1)
    edge(ax, Ar, Fr, 'a_reached, a_stowed', r=0.36, rad=0.35, off=-0.1, color=GREY)

    ax.text(6.4, 5.9, 'E2 (R5): трогаться со сложенной рукой', fontsize=11, weight='bold', color=NAVY)
    In, Out = (7.6, 4.5), (10.6, 4.5)
    state(ax, *In, 'In', init=True, marked=True, init_dir=(0, 1))
    state(ax, *Out, 'Out')
    edge(ax, In, Out, 'a_reach', rad=-0.3, off=0.1)
    edge(ax, Out, In, 'a_stowed', rad=-0.3, off=0.1, color=GREY)
    loop(ax, In[0], In[1], 'b_go_*', up=False)

    ax.text(0.3, 2.6, 'E3 (R6): закрывать захват на видимом предмете', fontsize=11, weight='bold', color=NAVY)
    N, Y = (1.6, 1.1), (4.4, 1.1)
    state(ax, *N, 'N', init=True, marked=True, init_dir=(0, 1))
    state(ax, *Y, 'Y', marked=True)
    edge(ax, N, Y, 'v_detect', rad=-0.3, off=0.1, color=GREY)
    edge(ax, Y, N, 'v_lost', rad=-0.3, off=0.1, color=GREY)
    loop(ax, Y[0], Y[1], 'g_close', up=False)

    ax.text(6.4, 2.6, 'E5 (R6): закрывать при выдвинутом манипуляторе', fontsize=11, weight='bold', color=NAVY)
    Nx, Ex = (7.6, 1.1), (10.6, 1.1)
    state(ax, *Nx, 'Nx', init=True, marked=True, init_dir=(0, 1))
    state(ax, *Ex, 'Ex', marked=True)
    edge(ax, Nx, Ex, 'a_reached', rad=-0.3, off=0.1, color=GREY)
    edge(ax, Ex, Nx, 'a_stow', rad=-0.3, off=0.1)
    loop(ax, Ex[0], Ex[1], 'g_close', up=False)
    save(fig, 'fig_03_specs.png')


# ------------------------------------------------------------------ 4. архитектура
def fig_architecture():
    fig, ax = canvas(12.0, 5.8, 'Архитектура контроллера: кто решает «что делать», кто - «что запрещено»')
    block(ax, 0.3, 3.3, 3.0, 1.5, 'Логика миссии\n(машина состояний;\nнавыки NavigateTo,\nGrasp, Place)', fc='#DCE6F7', fs=9.8)
    block(ax, 4.5, 3.3, 3.0, 1.5, 'Супервизор\nsupervisor_youbot.json\n324 состояния', fc='#DCF0E6', ec=GREEN, bold=True)
    block(ax, 8.7, 3.3, 3.0, 1.5, 'Webots: youBot\nприводы колёс, звеньев,\nпальцев', fc=BG)
    block(ax, 8.7, 0.6, 3.0, 1.5, 'Датчики\nGPS, IMU, камера,\nds_left/right,\nдатчики звеньев и пальцев', fc=BG, fs=9.8)
    block(ax, 4.5, 0.6, 3.0, 1.5, 'Формирование событий\nb_arrive, a_reached, g_ok,\ng_miss, v_detect, b_block', fc='#FFE9C7', ec=AMB)
    block(ax, 0.3, 0.6, 3.0, 1.5, 'Журнал и монитор R1\n(по физике сцены,\nнезависимо от модели)', fc='#F5DEDB', ec=RED)
    arrow(ax, (3.3, 4.25), (4.5, 4.25))
    ax.text(3.9, 4.55, 'allowed(e)?', ha='center', fontsize=9.5, style='italic', color=NAVY)
    arrow(ax, (7.5, 4.25), (8.7, 4.25), color=GREEN)
    ax.text(8.1, 4.55, 'разрешено', ha='center', fontsize=9.5, style='italic', color=GREEN)
    arrow(ax, (4.5, 3.75), (3.3, 3.75), color=RED, ls='--')
    ax.text(3.9, 3.45, 'запрещено:\nждать', ha='center', va='top', fontsize=9, style='italic', color=RED)
    arrow(ax, (10.2, 3.3), (10.2, 2.1))
    arrow(ax, (8.7, 1.35), (7.5, 1.35))
    arrow(ax, (6.0, 2.1), (6.0, 3.3), color=AMB)
    ax.text(6.15, 2.7, 'observe(e)', fontsize=9.5, style='italic', color=AMB, ha='left')
    arrow(ax, (4.5, 1.1), (3.3, 1.1), color=GREY)
    arrow(ax, (4.8, 2.1), (2.6, 3.3), color=AMB, rad=0.15)
    ax.text(3.2, 2.45, 'события', fontsize=9, style='italic', color=AMB)
    save(fig, 'fig_04_architecture.png')


# ------------------------------------------------------------------ 5. бюджет задержки
def vmax(dd, ds, T, a):
    A, B, C = 1 / (2 * a), T, -(dd - ds)
    return (-B + math.sqrt(B * B - 4 * A * C)) / (2 * A)


def fig_latency():
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12.0, 4.4), gridspec_kw={'width_ratios': [1, 1.25]})
    parts = [('опрос датчика', 16), ('передача', 16), ('обработка', 2), ('решение (цикл 10 Гц)', 100), ('привод', 16)]
    left = 0
    colors = ['#8FB3E0', '#B9CDE8', '#D6E2F2', AMB, '#8FB3E0']
    for (n, v), c in zip(parts, colors):
        a1.barh([0], [v], left=left, color=c, edgecolor='white')
        if v >= 15:
            a1.text(left + v / 2, 0, '%d' % v, ha='center', va='center', fontsize=10)
        left += v
    a1.set_yticks([])
    a1.set_xlim(0, 160)
    a1.set_xlabel('мс')
    a1.set_title('Контур объезда: T_total = 150 мс', fontsize=12, color=NAVY)
    for i, ((n, v), c) in enumerate(zip(parts, colors)):
        a1.text(2, -0.62 - i * 0.16, '■ ' + n, color=c if c != '#D6E2F2' else GREY, fontsize=9.5, va='center')
    a1.set_ylim(-1.5, 0.6)
    for s in ('top', 'right', 'left'):
        a1.spines[s].set_visible(False)

    dd = [0.1 + i * 0.02 for i in range(46)]
    a2.plot(dd, [vmax(d, 0.05, 0.150, 1.0) for d in dd], color=NAVY, lw=2, label='T_total = 150 мс (цикл 10 Гц)')
    a2.plot(dd, [vmax(d, 0.05, 0.066, 1.0) for d in dd], color=GREEN, lw=2, ls='--', label='T_total = 66 мс (по событию)')
    a2.axvline(0.1, color=RED, lw=1)
    a2.text(0.105, 1.25, 'дальность\nпо умолчанию\n0,1 м', color=RED, fontsize=9, va='top')
    a2.axhline(0.3, color=AMB, lw=1)
    a2.text(0.75, 0.33, 'принято в сцене: 0,3 м/с', color=AMB, fontsize=9)
    a2.scatter([0.1, 1.0], [vmax(0.1, 0.05, 0.15, 1), vmax(1.0, 0.05, 0.15, 1)], color=NAVY, zorder=5)
    a2.text(0.12, 0.12, '0,20 м/с', fontsize=9.5, color=NAVY)
    a2.text(0.9, 1.3, '1,24 м/с', fontsize=9.5, color=NAVY)
    a2.set_xlabel('дальность датчика расстояния d_detect, м')
    a2.set_ylabel('допустимая скорость v_max, м/с')
    a2.set_title('Что ограничивает скорость: дальность, а не цикл', fontsize=12, color=NAVY)
    a2.grid(alpha=0.3)
    a2.legend(fontsize=9, loc='lower right')
    fig.tight_layout()
    save(fig, 'fig_05_latency.png')


# ------------------------------------------------------------------ 6. трасса в блокировку
def fig_blocking():
    fig, ax = canvas(12.4, 3.4, 'Кратчайшая трасса в блокировку (модель без o_giveup)')
    seq = ['a_reach', 'a_reached', 'b_go_table', 'b_arrive', 'g_close', 'g_ok', 'g_slip']
    states = ['H S O Sr Tb', 'H R O Sr Tb', 'H X O Sr Tb', 'mT X O Sr Tb', 'T X O Sr Tb', 'T X C Sr Tb', 'T X D Sr Hn',
              'T X O Sr Fl']
    x0, stepx = 0.2, 1.53
    for i, st in enumerate(states):
        bad = i == len(states) - 1
        warn = i in (2, 3)
        fc = '#F5DEDB' if bad else ('#FFE9C7' if warn else BG)
        ec = RED if bad else (AMB if warn else NAVY)
        block(ax, x0 + i * stepx, 1.1, 1.25, 0.9, st.replace(' ', '\n', 2), fc=fc, ec=ec, fs=8.5, bold=bad)
        if i < len(seq):
            arrow(ax, (x0 + i * stepx + 1.25, 1.55), (x0 + (i + 1) * stepx, 1.55),
                  color=RED if seq[i] == 'g_slip' else NAVY, lw=1.3)
            ax.text(x0 + i * stepx + 1.39, 2.25, seq[i], ha='center', fontsize=8.8, style='italic',
                    color=RED if seq[i] == 'g_slip' else NAVY, rotation=0)
    ax.text(0.2, 0.55, 'Жёлтые - едет с выдвинутым манипулятором: объект это допускает, запрет даст спецификация E2.',
            fontsize=9.5, color=AMB)
    ax.text(0.2, 0.15, 'Красное - предмет на полу, маркированных состояний не достичь: 144 таких состояния.',
            fontsize=9.5, color=RED)
    ax.text(0.2, 2.8, 'порядок компонент: платформа, манипулятор, захват, восприятие, предмет', fontsize=9, color=GREY)
    save(fig, 'fig_06_blocking.png')


# ------------------------------------------------------------------ по журналам Webots
def load(name):
    with open(os.path.join(LOGS, name + '.json'), encoding='utf-8') as fh:
        return json.load(fh)


def load_csv(name):
    import csv
    with open(os.path.join(LOGS, name + '.csv'), encoding='utf-8') as fh:
        return list(csv.DictReader(fh))


def fig_plan():
    fig, ax = plt.subplots(figsize=(8.5, 6.2))
    ax.add_patch(Rectangle((0.305, -0.3), 0.6, 0.6, facecolor='#C9A66B', edgecolor='#8B6B3A', label='стол'))
    ax.add_patch(Rectangle((-1.05, -0.15), 0.3, 0.3, facecolor='#A98A5A', edgecolor='#6E5530', label='препятствие'))
    ax.add_patch(Rectangle((-0.7, -1.9), 0.2, 0.2, facecolor='#5B9BD5', edgecolor=BLUE, label='контейнер'))
    ax.add_patch(Rectangle((-2.15, -0.25), 0.7, 0.5, facecolor='#BFE0C8', edgecolor=GREEN, label='база'))
    for name, color, lab in (('video_obstacle', NAVY, 'с препятствием'), ('nominal_s1', AMB, 'без препятствия')):
        p = os.path.join(LOGS, name + '_traj.json')
        if not os.path.exists(p):
            continue
        tr = json.load(open(p))
        ax.plot([r[1] for r in tr], [r[2] for r in tr], color=color, lw=2, label='путь робота: ' + lab)
        ax.plot([r[4] for r in tr], [r[5] for r in tr], color=color, lw=1, ls=':')
    ax.set_aspect('equal')
    ax.set_xlim(-2.4, 1.1)
    ax.set_ylim(-2.1, 1.1)
    ax.grid(alpha=0.3)
    ax.set_xlabel('x, м')
    ax.set_ylabel('y, м')
    ax.set_title('План сцены и пути робота по журналам (пунктир - путь предмета)', fontsize=11, color=NAVY)
    ax.legend(fontsize=8.5, loc='upper left', bbox_to_anchor=(1.01, 1.0))
    fig.tight_layout()
    save(fig, 'fig_07_plan.png')


KIND_COLORS = {'cmd': NAVY, 'event': GREY, 'denied': RED, 'R1': RED, 'inject': AMB, 'fault': RED}


def fig_timeline(run='video_obstacle'):
    if not os.path.exists(os.path.join(LOGS, run + '.csv')):
        return
    rows = load_csv(run)
    t_end = float(rows[-1]['t']) + 2
    comp = [('платформа', 0), ('манипулятор', 1), ('захват', 2), ('восприятие', 3), ('предмет', 4)]
    fig, ax = plt.subplots(figsize=(12.0, 3.8))
    names = {0: {'H': 'база', 'mT': 'к столу', 'T': 'у стола', 'mB': 'к контейнеру', 'B': 'у контейнера',
                 'mH': 'на базу', 'sT': 'препятствие', 'sB': 'препятствие', 'sH': 'препятствие'},
             1: {'S': 'сложен', 'R': 'выдвигается', 'X': 'выдвинут', 'W': 'складывается'},
             2: {'O': 'открыт', 'C': 'закрывается', 'D': 'держит'},
             3: {'Sr': 'поиск', 'F': 'видит'},
             4: {'Tb': 'на столе', 'Hn': 'в захвате', 'Bx': 'в контейнере', 'Fl': 'на полу', 'Un': 'недоступен'}}
    pal = ['#DCE6F7', '#FFE9C7', '#DCF0E6', '#F5DEDB', '#E6E0F2', '#EFEFEF']
    for ci, (cname, idx) in enumerate(comp):
        segs = []
        cur, t0 = None, 0.0
        for r in rows:
            if r['model_state'] in ('', '-'):
                continue
            v = r['model_state'].split('/')[idx]
            if v != cur:
                if cur is not None:
                    segs.append((t0, float(r['t']), cur))
                cur, t0 = v, float(r['t'])
        segs.append((t0, t_end, cur))
        seen = {}
        for a, b, v in segs:
            c = pal[seen.setdefault(v, len(seen)) % len(pal)]
            y = len(comp) - 1 - ci
            ax.barh(y, b - a, left=a, color=c, edgecolor='white', height=0.8)
            if b - a > 2.2:
                ax.text((a + b) / 2, y, names[idx].get(v, v), ha='center', va='center', fontsize=8)
    ax.set_yticks(range(len(comp)))
    ax.set_yticklabels([c for c, _ in reversed(comp)])
    for r in rows:
        if r['kind'] in ('cmd',):
            ax.axvline(float(r['t']), color=NAVY, lw=0.4, alpha=0.4)
    ax.set_xlim(0, t_end)
    ax.set_xlabel('время моделирования, с (вертикальные линии - выданные команды)')
    ax.set_title('Состояние модели по журналу: миссия с объездом препятствия', fontsize=11, color=NAVY)
    fig.tight_layout()
    save(fig, 'fig_08_timeline.png')


def fig_slip():
    runs = [('slip_nomon_s1', 'без контроля зазора пальцев'), ('slip_mon_s1', 'с контролем зазора пальцев')]
    if not all(os.path.exists(os.path.join(LOGS, r + '_traj.json')) for r, _ in runs):
        return
    fig, axes = plt.subplots(1, 2, figsize=(12.0, 3.8), sharey=True)
    for ax, (run, title) in zip(axes, runs):
        tr = json.load(open(os.path.join(LOGS, run + '_traj.json')))
        ax.plot([r[0] for r in tr], [r[6] for r in tr], color=NAVY, lw=1.8, label='высота предмета, м')
        rows = load_csv(run)
        for r in rows:
            t = float(r['t'])
            if r['kind'] == 'inject':
                ax.axvline(t, color=AMB, lw=1.5)
                ax.text(t + 0.3, 0.3, 'предмет\nвыпал', color=AMB, fontsize=9)
            if r['name'] in ('g_slip',) and r['kind'] == 'event':
                ax.axvline(t, color=GREEN, lw=1.5, ls='--')
                ax.text(t + 0.3, 0.5, 'g_slip\nобнаружено', color=GREEN, fontsize=9)
            if r['name'] == 'g_put':
                ax.axvline(t, color=RED, lw=1.5, ls='--')
                ax.text(t + 0.3, 0.55, 'g_put:\n«уложен»', color=RED, fontsize=9)
            if r['name'] == 'o_giveup':
                ax.axvline(t, color=GREEN, lw=1.5)
                ax.text(t + 0.3, 0.35, 'o_giveup', color=GREEN, fontsize=9)
        s = load(run)
        verdict = 'модель: предмет %s; в контейнере: %s' % (s.get('model_object'), 'да' if s.get('object_in_box') else 'нет')
        ax.set_title('%s\n%s' % (title, verdict), fontsize=10.5, color=NAVY)
        ax.set_xlabel('время, с')
        ax.grid(alpha=0.3)
    axes[0].set_ylabel('высота предмета, м')
    fig.tight_layout()
    save(fig, 'fig_09_slip.png')


def fig_trials():
    files = [f for f in glob.glob(os.path.join(LOGS, '*.json')) if not f.endswith('_traj.json')]
    rows = [json.load(open(f, encoding='utf-8')) for f in files]
    order = ['nominal', 'obstacle', 'miss', 'shift35', 'slip_nomon', 'slip_mon', 'hasty_sup', 'hasty_nosup']
    labels = {'nominal': 'штатный', 'obstacle': 'препятствие', 'miss': 'промах\n(смещение 60 мм)',
              'shift35': 'смещение 35 мм:\nупор пальца', 'slip_nomon': 'выпадение,\nбез контроля',
              'slip_mon': 'выпадение,\nс контролем', 'hasty_sup': 'поспешная логика\n+ супервизор',
              'hasty_nosup': 'поспешная логика\nбез супервизора'}
    groups = {k: [r for r in rows if r['run'].rsplit('_s', 1)[0] == k] for k in order}
    groups = {k: v for k, v in groups.items() if v}
    ks = list(groups)
    fig, ax = plt.subplots(figsize=(12.0, 4.4))
    w = 0.2
    xs = range(len(ks))
    ok = [sum(bool(r['object_in_box']) and r['result'] == 'delivered' for r in groups[k]) for k in ks]
    gave = [sum(r['result'] == 'gave_up' for r in groups[k]) for k in ks]
    false = [sum(bool(r['false_success']) for r in groups[k]) for k in ks]
    r1 = [sum(r['r1_violation_episodes'] > 0 for r in groups[k]) for k in ks]
    n = [len(groups[k]) for k in ks]
    ax.bar([x - 1.5 * w for x in xs], n, w, color='#D6E2F2', label='прогонов')
    ax.bar([x - 0.5 * w for x in xs], ok, w, color=GREEN, label='предмет доставлен')
    ax.bar([x + 0.5 * w for x in xs], gave, w, color=AMB, label='помечен недоступным')
    ax.bar([x + 1.5 * w for x in xs], [f + 0.0 for f in false], w, color=RED, label='ложный успех')
    for x, v in zip(xs, r1):
        if v:
            ax.text(x, n[x] + 0.5, 'R1 нарушено\nв %d из %d' % (v, n[x]), ha='center', color=RED, fontsize=9, weight='bold')
    ax.set_xticks(list(xs))
    ax.set_xticklabels([labels[k] for k in ks], fontsize=9)
    for x, k in zip(xs, ks):
        faults = sum(r['result'] not in ('delivered', 'gave_up') for r in groups[k])
        if faults:
            kinds = sorted({r['result'] for r in groups[k] if r['result'] not in ('delivered', 'gave_up')})
            ax.text(x, n[x] + 0.5, ('отказ: %d' + chr(10) + '(%s)') % (faults, ', '.join(kinds)), ha='center', color=GREY, fontsize=8.5)
    ax.set_ylim(0, max(n) + 2.2)
    ax.set_ylabel('число прогонов')
    ax.set_title('Итоги испытаний в Webots по сценариям', fontsize=11, color=NAVY)
    ax.legend(fontsize=9, ncol=4, loc='upper right', bbox_to_anchor=(1.0, 1.0))
    ax.grid(axis='y', alpha=0.3)
    fig.tight_layout()
    save(fig, 'fig_10_trials.png')


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'logs':
        fig_plan()
        fig_timeline()
        fig_slip()
        fig_trials()
    else:
        fig_base()
        fig_components()
        fig_specs()
        fig_architecture()
        fig_latency()
        fig_blocking()
