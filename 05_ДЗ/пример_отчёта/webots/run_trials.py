# -*- coding: utf-8 -*-
"""Прогоны сценариев испытаний в Webots и сводная таблица.

  python run_trials.py world                 записать worlds/youbot_mission.wbt (штатный мир)
  python run_trials.py trials                все сценарии раздела 6 без отрисовки
  python run_trials.py video                 штатный прогон с объездом препятствия: видео и снимки
  python run_trials.py summary               сводка по logs/*.json

Webots должен быть установлен; путь к нему - переменная WEBOTS_HOME или
C:\\Program Files\\Webots. Путь к проекту не должен содержать кириллицы:
при необходимости скопируйте каталог пример_отчёта во временную папку.
"""
import glob
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WEBOTS_HOME = os.environ.get('WEBOTS_HOME', r'C:\Program Files\Webots')
WEBOTS = os.path.join(WEBOTS_HOME, 'msys64', 'mingw64', 'bin', 'webots.exe')

HEADER = '''#VRML_SIM R2025a utf8

EXTERNPROTO "https://raw.githubusercontent.com/cyberbotics/webots/R2025a/projects/objects/backgrounds/protos/TexturedBackground.proto"
EXTERNPROTO "https://raw.githubusercontent.com/cyberbotics/webots/R2025a/projects/objects/backgrounds/protos/TexturedBackgroundLight.proto"
EXTERNPROTO "https://raw.githubusercontent.com/cyberbotics/webots/R2025a/projects/objects/floors/protos/Floor.proto"
EXTERNPROTO "https://raw.githubusercontent.com/cyberbotics/webots/R2025a/projects/objects/factory/containers/protos/WoodenBox.proto"
EXTERNPROTO "https://raw.githubusercontent.com/cyberbotics/webots/R2025a/projects/robots/kuka/youbot/protos/Youbot.proto"

WorldInfo {
  info [ "Пример отчёта по ДЗ УРТК: миссия youBot под надзором синтезированного супервизора" ]
  title "youBot mission"
  basicTimeStep 16
  contactProperties [
    ContactProperties { material1 "InteriorWheelMat" coulombFriction [ 0, 2, 0 ] frictionRotation -0.785398 0 bounce 0 forceDependentSlip [ 10, 0 ] }
    ContactProperties { material1 "ExteriorWheelMat" coulombFriction [ 0, 2, 0 ] frictionRotation 0.785398 0 bounce 0 forceDependentSlip [ 10, 0 ] }
  ]
}
DEF VIEW Viewpoint {
  orientation 0.2539 0.541 -0.8018 1.0593
  position -3.0 2.3 2.7
}
TexturedBackground {
}
TexturedBackgroundLight {
}
Floor {
  size 8 8
}
DEF TABLE WoodenBox {
  translation 0.605448 0.00121984 0.2
  rotation 0 0 1 -1.5707963267948966
  name "table"
  size 0.6 0.6 0.4
}
DEF TARGET Solid {
  translation 0.472629 0.00710068 0.4126
  children [
    Shape {
      appearance PBRAppearance { baseColor 0.8 0.1 0.1 roughness 0.5 metalness 0 }
      geometry DEF CUBE Box { size 0.025 0.025 0.025 }
    }
  ]
  name "target"
  model "target"
  boundingObject USE CUBE
  physics Physics { density 2700 }
  recognitionColors [ 0.8 0.1 0.1 ]
}
DEF CONTAINER Solid {
  translation -0.6 -1.8 0.002
  children [
    Shape {
      appearance PBRAppearance { baseColor 0.1 0.45 0.8 roughness 0.8 metalness 0 }
      geometry Box { size 0.2 0.2 0.004 }
    }
  ]
  name "container"
}
DEF HOME Solid {
  translation -1.8 0 0.001
  children [
    Shape {
      appearance PBRAppearance { baseColor 0.2 0.6 0.3 roughness 0.8 metalness 0 }
      geometry Box { size 0.7 0.5 0.002 }
    }
  ]
  name "home"
}
'''

OBSTACLE = '''DEF OBSTACLE WoodenBox {
  translation -0.9 0 0.15
  name "obstacle"
  size 0.3 0.3 0.3
}
'''

ROBOT = '''DEF ROBOT Youbot {
  translation -1.8 0 0.102838
  controller "youbot_mission"
  controllerArgs [ %s ]
  supervisor TRUE
  bodySlot [
    GPS {
    }
    InertialUnit {
    }
    Pose {
      translation 0.25 -0.17 0.2
      children [
        Shape {
          appearance PBRAppearance { baseColor 0.3 0.3 0.3 roughness 0.6 metalness 0.3 }
          geometry Cylinder { height 0.4 radius 0.01 }
        }
      ]
    }
    Camera {
      translation 0.25 -0.17 0.42
      rotation 0 1 0 0.35
      name "camera"
      fieldOfView 0.9
      width 640
      height 480
      recognition Recognition {
      }
    }
    DistanceSensor {
      translation 0.3 0.1 0
      name "ds_left"
      lookupTable [ 0 0 0, 1 1 0 ]
    }
    DistanceSensor {
      translation 0.3 -0.1 0
      name "ds_right"
      lookupTable [ 0 0 0, 1 1 0 ]
    }
  ]
}
'''


def world_text(args, obstacle):
    quoted = ' '.join('"%s"' % a for a in args)
    return HEADER + (OBSTACLE if obstacle else '') + ROBOT % quoted


def run(name, args, obstacle=False, render=False):
    path = os.path.join(HERE, 'worlds', '_%s.wbt' % name)
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(world_text(args + ['run=%s' % name], obstacle))
    cmd = [WEBOTS, '--mode=fast', '--batch', '--stdout', '--stderr', path]
    cmd.insert(1, '--minimize')
    if not render:
        cmd.insert(1, '--no-rendering')
    out = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=900)
    os.remove(path)
    line = [l for l in out.stdout.splitlines() if l.startswith('SUMMARY')]
    print('%-28s %s' % (name, line[0][8:] if line else 'НЕТ ИТОГА\n' + out.stdout[-2000:] + out.stderr[-2000:]),
          flush=True)


TRIALS = (
    [('nominal_s%d' % s, ['scenario=nominal', 'seed=%d' % s], False) for s in range(1, 11)] +
    [('obstacle_s%d' % s, ['scenario=obstacle', 'seed=%d' % s], True) for s in range(1, 6)] +
    [('miss_s%d' % s, ['scenario=miss', 'shift=0.06', 'seed=%d' % s], False) for s in range(1, 6)] +
    [('shift35_s%d' % s, ['scenario=miss', 'shift=0.035', 'seed=%d' % s], False) for s in range(1, 6)] +
    [('slip_nomon_s%d' % s, ['scenario=slip', 'monitor=0', 'seed=%d' % s], False) for s in range(1, 6)] +
    [('slip_mon_s%d' % s, ['scenario=slip', 'monitor=1', 'seed=%d' % s], False) for s in range(1, 6)] +
    [('hasty_sup_s%d' % s, ['scenario=hasty', 'sup=1', 'seed=%d' % s], False) for s in range(1, 4)] +
    [('hasty_nosup_s%d' % s, ['scenario=hasty', 'sup=0', 'seed=%d' % s], False) for s in range(1, 4)]
)


def summary():
    rows = [json.load(open(f, encoding='utf-8')) for f in sorted(glob.glob(os.path.join(HERE, 'logs', '*.json')))
            if not f.endswith('_traj.json')]
    groups = {}
    for r in rows:
        key = r['run'].rsplit('_s', 1)[0]
        groups.setdefault(key, []).append(r)
    print('%-14s %3s %9s %7s %8s %7s %6s %9s %8s' % ('сценарий', 'n', 'доставлен', 'в конт.', 'ложн.усп', 'отказ', 'R1', 'запретов', 'время,с'))
    for k, rs in groups.items():
        n = len(rs)
        print('%-14s %3d %9d %7d %8d %7d %6d %9.1f %8.1f' % (
            k, n,
            sum(r['result'] == 'delivered' for r in rs),
            sum(bool(r['object_in_box']) for r in rs),
            sum(bool(r['false_success']) for r in rs),
            sum(r['result'] == 'gave_up' for r in rs),
            sum(r['r1_violation_episodes'] for r in rs),
            sum(r['denied'] for r in rs) / n,
            sum(r['time_s'] for r in rs) / n))


if __name__ == '__main__':
    what = sys.argv[1] if len(sys.argv) > 1 else 'summary'
    only = sys.argv[2] if len(sys.argv) > 2 else None
    if what == 'world':
        with open(os.path.join(HERE, 'worlds', 'youbot_mission.wbt'), 'w', encoding='utf-8') as fh:
            fh.write(world_text(['scenario=obstacle', 'seed=0', 'run=manual'], True))
    elif what == 'trials':
        for name, args, obst in TRIALS:
            if only is None or name.startswith(only):
                run(name, args, obst)
        summary()
    elif what == 'video':
        run('video_obstacle', ['scenario=obstacle', 'seed=0', 'record=1'], True, render=True)
    else:
        summary()
