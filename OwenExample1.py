import time
import Owen
import serial

OWEN_COMPORT = 'COM8'
OWEN_SPEED = 115200

com = serial.Serial(OWEN_COMPORT, OWEN_SPEED, timeout=1)  # открываем порт, нумерация начинается с 0)
owenDev = Owen.OwenDevice(com, 1)  # порт, адрес устройства

print('Прибор: {}'.format(owenDev.getDeviceName()))
print('Прошивка: {}'.format(owenDev.getFirmwareVersion()))
print(owenDev.getNetworkSettings())

rs = owenDev.getChar('r-S')  # Уставка
pv = owenDev.getFloat24('PV')  # Вкл./выкл. PID
sp = owenDev.getFloat24('SP')  # Текущее значение

print('SP = {:.2f} °C, PV = {:.2f} °C, PID = {}'.format(sp, pv, rs))

sp = owenDev.writeFloat24('SP', 29.4)
print('Изменение уставки SP = {:.2f} °C'.format(sp))

rs = owenDev.writeChar('r-S', True)
print('Команда запуска PID. PID = {}'.format(rs))

'''
Старый неработающий код. Оставлен только для общей информации 
#создаем последовательный порт
try:
    # COM = MySerial.ComPort('COM8', 115200, timeout=1)#открываем COM12 (нумерация портов начинается с 0)
    COM = serial.Serial('COM7', 115200, timeout=3)#открываем COM12 (нумерация портов начинается с 0)
    #COM = MySerial.ComPort(0, 9600, timeout=1)#открываем COM1 (нумерация портов начинается с 0)
except:
    raise Exception('Error openning port!')

COM.LoggingIsOn=True#включаем логирование в файл

#создаем устройство
#owenDev=Owen.Owen(None,16);#тестовые данные
owenDev=Owen.OwenDevice(COM, 1); # порт, адрес устройства
owenDev.Debug = True  # включем отладочные сообщения

result = owenDev.getChar('r-S')
print('Read r-S: {}'.format(result))


result = owenDev.writeFloat24('SP', 42.5)
print('Write SP: {}'.format(result))
result = owenDev.writeChar('r-S', 0)
print('Write r-S: {}'.format(result))

#Только для ТРМ251
if devName == 'TPM251':
    result = owenDev.getIEEE32('r.oUt')
    print('Output power: {}'.format(result))

#читаем с базового адреса
result=owenDev.getFloat24('PV')
print('PV: {}'.format(result))
#result1=owenDev.GetIEEE32(b'rEAd',0,withTime=True)['value']


#пример обработки исколЮчения, анализирует ошибку обрыв термопары
try:
    #читаем с адреса базовый+1
    result1 = owenDev.getFloat24('PV', 2)
    # result2=owenDev.GetIEEE32(hashREAD,1,withTime=True)
except Owen.OwenUnpackError as e:
    #обрабатываем ошибку раскодировки данных
    result2 = None
    if len(e.data) == 1:
        #это код ошибки                
        if ord(e.data[0]) == 0xfd:
            #это обрыв термопары
            print('Owen device::Sensor is damaged!')
    else:
        #бросаем исклЮчение дальше
        raise Exception('Owen device::Error when getting value!')
except:
    #бросаем исключение дальше
    raise Exception('Owen device::Error when getting value!')
print('Response from base address: ',result1)
print('Response from base+1 address: ',result2)
'''