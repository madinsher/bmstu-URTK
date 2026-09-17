# -*- coding: utf-8 -*-
"""Исполнитель супервизора для контроллера Webots.

Загружает таблицу, построенную des_youbot.py, и делает ровно две вещи:
  - allowed(e)  -> можно ли сейчас выдать команду, порождающую управляемое событие e;
  - observe(e)  -> продвинуть состояние по наблюдённому событию.

Навыки (SMACH-состояния, дерево поведения, простой цикл) решают, ЧТО делать;
супервизор решает, ЧТО ЗАПРЕЩЕНО. Любая попытка выдать запрещённую команду
отклоняется и журналируется - это и есть «защитный фильтр» между логикой
миссии и приводами.

Пример использования в контроллере:

    sup = Supervisor('supervisor_youbot.json')
    ...
    if sup.allowed('b_go_box'):
        base.go_to(BOX_POSE)
        sup.observe('b_go_box')          # команда выдана - событие произошло
    ...
    if base.arrived():
        sup.observe('b_arrive')          # неуправляемое событие от датчиков
"""
import json


class SupervisorViolation(RuntimeError):
    pass


class Supervisor:
    def __init__(self, path):
        with open(path, encoding='utf-8') as fh:
            t = json.load(fh)
        self.states = {s['id']: s for s in t['states']}
        self.uc = set(t['uncontrollable'])
        self.uo = set(t['unobservable'])
        self.state = t['initial']
        self.log = []

    def allowed(self, event):
        ok = event in self.states[self.state]['enabled_controllable']
        if not ok:
            self.log.append(('denied', self.state, event))
        return ok

    def observe(self, event):
        if event in self.uo:
            raise ValueError('событие %s объявлено ненаблюдаемым и не может поступать' % event)
        nxt = self.states[self.state]['next'].get(event)
        if nxt is None:
            # неуправляемое событие, которого нет в модели, - расхождение модели и объекта
            raise SupervisorViolation('событие %s невозможно в состоянии %s %s' % (
                event, self.state, self.states[self.state]['plant']))
        self.log.append(('event', self.state, event, nxt))
        self.state = nxt

    def plant_state(self):
        return self.states[self.state]['plant']


if __name__ == '__main__':
    sup = Supervisor('supervisor_youbot.json')
    mission = ['b_go_table', 'b_arrive', 'a_reach', 'a_reached', 'v_detect', 'g_close', 'g_ok',
               'a_stow', 'a_stowed', 'b_go_box', 'b_arrive', 'a_reach', 'a_reached', 'g_put',
               'a_stow', 'a_stowed', 'b_go_home', 'b_arrive']
    for e in mission:
        if e not in sup.uc and not sup.allowed(e):
            print('запрещено:', e, sup.plant_state())
            break
        sup.observe(e)
    print('конечное состояние объекта:', sup.plant_state(),
          'маркировано:', sup.states[sup.state]['marked'])
    # попытка тронуться с выдвинутым манипулятором
    sup2 = Supervisor('supervisor_youbot.json')
    for e in ['b_go_table', 'b_arrive', 'a_reach', 'a_reached']:
        sup2.observe(e)
    print('b_go_box с выдвинутым манипулятором разрешён?', sup2.allowed('b_go_box'))
