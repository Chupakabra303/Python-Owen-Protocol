import builtins
from threading import Thread
from queue import Queue, Empty
import time
import os
import OwenWithQueue
import serial

from tkinter import *
from tkinter.messagebox import *
from tkinter.scrolledtext import *

OWEN_COMPORT = 'COM8'
OWEN_SPEED = 115200

def OwenIODaemon():
    global owenDevError
    global com, pv, rs, sp
    queueLogMsg.put("OwenIO daemon запущен")
    while not stop_threads:
        try:
            owenDevError = False
            if not com.isOpen():
                com = serial.Serial(OWEN_COMPORT, OWEN_SPEED, timeout=1)  # открываем порт, нумерация начинается с 0)
                queueLogMsg.put('Открыт порт {} ({})'.format(com.port, id(com)))
                owenDev.serialPort = com  # подключаем к новому дескриптору порта
                queueLogMsg.put('Прибор: {}'.format(owenDev.getDeviceName()))
                queueLogMsg.put('Прошивка: {}'.format(owenDev.getFirmwareVersion()))
                queueLogMsg.put(owenDev.getNetworkSettings())

            rs = owenDev.getChar('r-S')
            pidOnOffButtonState(rs)
            pv = owenDev.getFloat24('PV')
            sp = owenDev.getFloat24('SP')
            if not spScale.lock:
                spScale.set(sp)
            queueLogMsg.put('SP = {:.2f} °C, PV = {:.2f} °C, PID = {}, lock = {}'.format(sp, pv, rs, spScale.lock))

            cmd, val = owenDev.queueCmd.preview(timeout=1)  # предпросмотр команды из очереди
            if cmd == 'r-S':
                rs = owenDev.writeChar('r-S', val)
                owenDev.queueCmd.get(timeout=0) # извлечение команды из очереди только после удачной записи!
                queueLogMsg.put('Команда запуска PID. PID = {}'.format(rs)) if rs else queueLogMsg.put('Команда остановки PID. PID = {}'.format(rs))
            elif cmd == 'SP':
                sp = owenDev.writeFloat24('SP', val)
                owenDev.queueCmd.get(timeout=0)  # извлечение команды из очереди только после удачной записи!
                queueLogMsg.put('Изменение уставки SP = {:.2f} °C'.format(sp))
        except Empty:
            # queueLogMsg.put("timeout очереди")
            pass
        except Exception as e:
            owenDevError = True
            queueLogMsg.put(e)
            com.close()
            queueLogMsg.put('Закрыт порт {} ({})'.format(OWEN_COMPORT, id(com)))
            time.sleep(1)

    print("OwenIO daemon остановлен")

def writeToLog(msg):
    # https://tkdocs.com/tutorial/text.html#basics
    numlines = int(log.index('end - 1 line').split('.')[0])
    log['state'] = NORMAL
    if numlines > 100:
        log.delete(1.0, 'end - 100 line')
    # if log.index('end - 1 char')!='1.0':
    # log.insert('end', '\n')
    log.insert(END, msg)
    log.insert(END, '\n')
    log.see('end - 1 line')
    log['state'] = DISABLED

def textClear():
    log['state'] = NORMAL
    log.delete("1.0", END)
    log['state'] = DISABLED

def on_closing():
    if askokcancel("Выход", "Завершить работу?"):
        window.destroy()

def windowTimer1(interval=1000):
    if (owenDevError):
        errorLabelOwen.configure(text="Нет связи\nОвен ТРМ", bg="orange")
    else:
        errorLabelOwen.configure(text="", bg=defaultColor)
    try:
        while True:
            writeToLog(queueLogMsg.get_nowait())
    except Empty:
        pass
    window.after(interval, windowTimer1, interval)

# ------------------------
global queueLogMsg
builtins.queueLogMsg = Queue()  # создаем глобальную очередь для журнала в модуле builtins

com = serial.Serial()  # создаем объект порта
owenDev = OwenWithQueue.OwenDevice(com, 1)  # порт, адрес устройства
owenDevError = False
sp = 0  # Уставка
rs = False  # Вкл./выкл. PID
pv = 0  # Текущее значение

window = Tk()

window.title(os.path.basename(__file__))
window.protocol("WM_DELETE_WINDOW", on_closing)
window.geometry("{}x{}".format(int(window.winfo_screenwidth()*0.8), int(window.winfo_screenheight()*0.8)))
# window.geometry("{}x{}".format(window.winfo_screenwidth()//3, window.winfo_screenheight()//3))

topFrame = Frame(window, borderwidth=2)
bottomFrame = Frame(window)
topFrame.pack(padx=0, expand=0, fill=BOTH)
bottomFrame.pack(padx=0, expand=1, fill=BOTH)
defaultColor = topFrame.cget('bg')

# Button(topFrame, text="CN", width=15, height=2, command=lambda: sfp.write(b'CN'))\
#    .grid(row=0, column=0, pady=2, padx=2)
# Button(topFrame, text="CY", width=15, height=2, command=lambda: sfp.write(b'CY'))\
#    .grid(row=0, column=1)
Label(topFrame, text="Вкл./выкл. PID").grid(row=0, column=0)
Label(topFrame, text="Уставка SP").grid(row=0, column=1)

pidOnOffButton = Button(topFrame, text="?", width=15, height=2, command=lambda: owenDev.queueCmd.putCmd('r-S', not rs))
pidOnOffButton.grid(row=1, column=0, padx=2)

def pidOnOffButtonState(state):
    pidOnOffButton.configure(text="PID\n(Запущен)", bg="lime") if state else pidOnOffButton.configure(text="PID\n(Остановлен)", bg=defaultColor)

spScale = Scale(topFrame, from_=0, to=100, tickinterval=50, orient=HORIZONTAL)
spScale.lock = False  # добавляем новый атрибут "блокировка" (запрет изменения значения из OwenIODaemon)
spScale.bind("<Button-1>", lambda e: setattr(e.widget, 'lock', True))  # блокируем Wiget на изменение значения из OwenIODaemon
spScale.bind("<ButtonRelease-1>", lambda e: (owenDev.queueCmd.putCmd('SP', e.widget.get()), setattr(e.widget, 'lock', False)))

# spScale.bind("<Button-1>", lambda event: globals().update(spScaleLock=True))
# spScale.bind("<ButtonRelease-1>", lambda event: [owenDev.queueCmd.putCmd('SP', spScale.get()), globals().update(spScaleLock=False)])

spScale.grid(row=1, column=1, padx=2)
errorLabelOwen = Label(topFrame, text="", width=12, height=2, bg=defaultColor)
errorLabelOwen.grid(row=1, column=3, padx=2)

Button(topFrame, text="Очистить вывод", width=15, height=2, command=textClear).grid(row=1, column=4)

log = ScrolledText(bottomFrame, height=7)
log.pack(padx=2, expand=1, fill=BOTH)
window.update()

windowTimer1(100)  # запуск 100мс цикла функций в потоке графики

stop_threads = False
t1 = Thread(target=OwenIODaemon, daemon=True)
t1.start()
window.mainloop()
stop_threads = True
t1.join()
print("Работа завершена")