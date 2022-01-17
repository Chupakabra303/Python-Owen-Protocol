import struct
from queue import Queue, Empty, Full
from time import monotonic as time
from threading import Lock

class OwenError(Exception):
    """Базовый класс для исключений"""
    pass

class OwenProtocolError(OwenError):
    """Исключение вызвано ошибкой в протоколе (выход за границы дипазонов, отсутствие данных и др.)
    Attributes:        
        msg  -- текст ошибки
    """
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
       return repr(self.msg)

class OwenUnpackError(OwenError):
    """ИсклЮчение вызвано ошибкой распаковки данных
    Attributes:        
        msg  -- текст ошибки
        data -- данные
    """
    def __init__(self, msg, data):
        self.msg = msg
        self.data = data
    def __str__(self):
       return repr('{} Data: {}'.format(self.msg,list(self.data)))

class OwenProtocol:  # Класс, реализующий протокол ОВЕН напрямую в python
    # maxFrameSize = 21 # максимальная длина пакета согласно протоколу ОВЕН
    def __init__(self, serialPort, address, addrLen=8):
        # self.data = b''  # данные для передачи
        # self.dataSize = 0 # количество полученных байтов
        self.frame = bytearray()  # фрейм
        self.rawFrame = bytearray()  # низкоуровневый фрейм
        self.serialPort = serialPort  # класс последовательного порта
        self.address = address
        self.addrLen = addrLen  # длина адреса, может быть 8 или 11 бит
        # self.request = False #признак запроса
        # self.maxRawFrameSize = 44 #максимальная длина Raw-пакета включая маркеры
        self.Debug = False  # режим вывода отладочных сообщений
        self.mutex = Lock()

    def DebugMessage(self, message):#вывод отладочных сообщений
        if self.Debug:
            print(message)

    def __str__(self):
        return ('Address: {} Address length: {}\nHash: {} Request: {}\nData size: {} Data: {}\n'+\
                'Frame: {}\nFrame in Raw: {}\nCrc: {} Crc is OK: {}').format(self.address,self.addrLen,self.hash,self.request,self.dataSize,list(self.data),\
                                                         list(self.frame),self.rawFrame,self.crc,self.crcOk)

    def appendIndexAndTime(self,index = -1, time = -1):
        if not time == -1:
            self.data += chr((time >> 8) & 0x0f)
            self.data += chr(time & 0x0f)
        if not index == -1:
            self.data += chr((index >> 8) & 0x0f)
            self.data += chr(index & 0x0f)

    def owenCRC16(self, data):
        crc = 0
        for b in data:
            crc ^= b << 8
            for i in range(8):
                if (crc & 0x8000):
                    crc = (crc << 1) & 0xFFFF ^ 0x8F57
                else:
                    crc = (crc << 1) & 0xFFFF
        return crc

    def owenHASH(self, data):
        crc = 0
        for b in data:
            crc ^= (b << 9) & 0xFF00
            for i in range(7):
                if (crc & 0x8000):
                    crc = (crc << 1) & 0xFFFF ^ 0x8F57
                else:
                    crc = (crc << 1) & 0xFFFF
        return crc

    def name2hash(self, name: str):
        """Преобразование локального идентификатора в двоичный вид, name - строка, содержащая имя локального идентификатора"""
        id = [78, 78, 78, 78]
        j = 0
        for ch in name:
            byte = 0            
            if '0' <= ch <= '9':
                id[j] = (ord(ch) - ord('0')) * 2
            elif 'a' <= ch <= 'z':
                id[j] = (10 + ord(ch) - ord('a')) * 2
            elif 'A' <= ch <= 'Z':
                id[j] = (10 + ord(ch) - ord('A')) * 2
            elif '-' == ch:
                id[j] = 36 * 2
            elif '_' == ch:
                id[j] = 37 * 2
            elif '/' == ch:
                id[j] = 38 * 2
            elif '.' == ch:
                id[j-1] += 1
                continue
            elif (ch == ' '):
                break  # пробел может находиться только в конце имени
            else:
                # недопустимый символ
                raise OwenProtocolError('OwenProtocol::Illegal symbol in name {} !'.format(name))            
            j += 1
        return self.owenHASH(id)

    def packIEEE32(self, value):  # упаковываем число с плавающей точкой для передачи на устройство
        return struct.pack('>f', value)
    
    def packInt16(self, value):  # упаковываем целое число для передачи на устройство
        return struct.pack('>H', value)

    # !!!!
    def packFloat24(self, value):  # упаковываем число с плавающей точкой для передачи на устройство
        #print 'inPackingFloat24', value, '=', repr(self.data)
        return struct.pack('>f', value)[:-1]

    def packString(self, value):
        return value[::-1]

    def packChar(self, value):  # пакует байт
        return struct.pack('b', value)

    def unpackIEEE32(self, data, withTime = False, withIndex = False):  # извлекает из данных число с плавающей точкой и время
        dataSize = len(data)
        additionalBytes = 0
        if withTime:
            additionalBytes += 2
        if withIndex:
            additionalBytes += 2
        if dataSize != 4 + additionalBytes:
            raise OwenUnpackError('OwenUnpackError: Wrong size of data ({0}) when IEEE32 unpacking, should be {1}!'.format(dataSize, (4 + additionalBytes)),\
                                  data)
        value = struct.unpack('>f', data[0:4])[0]
        if withTime:
            timePos = 4
            time = (((data[timePos] & 0xff) << 8) | (data[timePos+1] & 0xff )) & 0xffff
        else:
            time = None
        if withIndex:
            indexPos = 2 + additionalBytes
            index = (((data[indexPos] & 0xff) << 8) | (data[indexPos+1] & 0xff )) & 0xffff
        else:
            index = None
        # result = dict(value = value, time = time, index = index)
        return value, time, index
    
    def unpackFloat24(self, data):  # извлекает из данных число с плаваЮщей точкой
        dataSize = len(data)
        if dataSize != 3:
            raise OwenUnpackError('OwenUnpackError: Wrong size of data ({0}) when float24 unpacking!'.format(dataSize), data)
        # value = struct.unpack('>f', data[0:3] + b'\x00')[0]
        # result = dict(value = value, time = -1, index = -1)
        return struct.unpack('>f', data[0:3] + b'\x00')[0]

    def unpackInt16(self, data):  # извлекает из данных целое число со знаком
        dataSize = len(data)
        if dataSize < 1:
            raise OwenUnpackError('OwenUnpackError: Wrong size of data ({}) when short int unpacking!'.format(dataSize), data)
        elif dataSize == 1:
            data = b'\x00' + data  # дополняем до двух байтов
        # value = ord(self.data[1]) + (ord(self.data[0])<<8 & 0xffff)
        # value = struct.unpack('>h', data[0:2])[0]
        # result = dict(value = value, time = -1, index = -1)
        return struct.unpack('>h', data[0:2])[0]

    def unpackUnsignedInt16(self, data):  # извлекает из данных целое число со знаком
        dataSize = len(data)
        if dataSize < 1:
            raise OwenUnpackError('OwenUnpackError: Wrong size of data ({}) when unsigned short int unpacking!'.format(dataSize), data)
        elif dataSize == 1:
            data = b'\x00' + data  # дополняем до двух байтов
        # value = ord(self.data[1]) + (ord(self.data[0])<<8 & 0xffff)
        # value = struct.unpack('>H', data[0:2])[0]
        # result = dict(value = value, time = -1, index = -1)
        return struct.unpack('>H', data[0:2])[0]

    def unpackString(self, data):  # распаковываем строку
        # value = struct.unpack('>{0}s'.format(len(self.data)),self.data)[0] #почему-то не инвертирует порядок байтов
        # value = data[::-1] # обратный порядок
        # result = dict(value = value, time = -1, index = -1)
        return data[::-1] # обратный порядок
        
    def unpackChar(self, data):  # извлекает из данных байт со знаком, возвращает целый тип
        dataSize = len(data)
        if dataSize != 1:
            raise OwenUnpackError('OwenUnpackError: Wrong size of data ({0}) when char unpacking!'.format(dataSize), data)
        # value = struct.unpack('b', data[:1])[0]
        # result = dict(value = value, time = -1, index = -1)
        return struct.unpack('b', data[:1])[0]

    def unpackUnsignedChar(self, data):#извлекает из данных байт без знака, возвращает целый тип
        dataSize = len(data)
        if dataSize != 1:
            raise OwenUnpackError('OwenUnpackError: Wrong size of data ({0}) when char unpacking!'.format(dataSize), data)
        # value = struct.unpack('B', data[0])[0]
        # result = dict(value = value, time = -1, index = -1)
        return struct.unpack('B', data[0])[0]
    
    def unpackFrame(self): # расшифровка пакета, проверка контрольной суммы
        if len(self.frame) < 6:
            raise OwenProtocolError('OwenProtocolError: Small length of frame!')
        # контрольная сумма
        crc = self.frame[-2] << 8 | self.frame[-1]
        # int.from_bytes(str1[-2:], 'big')
        if crc != self.owenCRC16(self.frame[:-2]):
            raise OwenProtocolError('OwenProtocolError: CRC mismatch!')
        # ВНИМАНИЕ: невозможно отличить 11-битые адреса кратные 8 от 8-битных
        ''' if frame[1] & 0xE0 == 0xE0:
            address = ((frame[0] << 3) & 0xff) | ((frame[1] >> 5) & 0xff)
            addrLen = 11
        else:
            address = frame[0]
            addrLen = 8 '''
        # запрос
        request = (self.frame[1] & 0x10) != 0
        # хэш
        # self.hash = ((self.frame[2] << 8) & 0xff) | self.frame[3]
        hash = self.frame[2] << 8 | self.frame[3]
        #размер данных
        dataSize = self.frame[1] & 0x0F
        if dataSize > 0:
            if dataSize != len(self.frame) - 6:
                raise OwenProtocolError('OwenProtocolError: Wrong data size value in frame!')
            data = bytes(self.frame[4:4+dataSize])
        else:
            data = b''
        return hash, data

    def unpackRawFrame(self, rawFrame: bytes):
        self.frame.clear()
        if rawFrame[0] != ord('#') or rawFrame[-1] != ord('\r'):
            raise OwenProtocolError('OwenProtocolError: Raw buffer does not have start or stop bytes!')
        for i in range(1, len(rawFrame) - 2, 2):
            self.frame.append((rawFrame[i] - 71) << 4 | (rawFrame[i + 1] - 71))  # склеиваем тетрады
        # return frame

    def packFrame(self, hash, address, request, data):  # формирует массив байтов из данных класса для передачи на устройство, возвращает фрейм в виде b строки
        self.frame.clear()
        # frame = bytearray()
        # адрес
        if self.addrLen == 8:
            self.frame.append(address & 0xff)
            self.frame.append(0)
        else:
            self.frame.append((address >> 3) & 0xff)
            self.frame.append((address & 0x07) << 5)
        # признак запроса
        if request:
            self.frame[1] |= 0x10
        else:
            self.frame[1] |= len(data)  # размер данных
        # хэш
        self.frame.append((hash >> 8) & 0xff)
        self.frame.append(hash & 0xff)
        # данные
        self.frame.extend(data)
        # контрольная сумма
        crc = self.owenCRC16(self.frame)
        self.frame.append((crc >> 8) & 0xff)
        self.frame.append(crc & 0xff)
        # frameStr += crc.to_bytes(2, 'big')
        # return frame

    def packRawFrame(self):  # преобразуем бинарные данные в строковый вид
        self.rawFrame.clear()
        # rawFrame = bytearray()
        self.rawFrame.append(ord('#'))  # стартовый символ
        for b in self.frame:
            self.rawFrame.append(0x47 + (b >> 4))  # первая тетрада
            self.rawFrame.append(0x47 + (b & 0x0F))  # вторая тетрада
        self.rawFrame.append(ord('\r'))
        # return rawFrame

    def getPingPong(self, address, name, request=True, data=b''):  # отправка фрейма запроса, получение ответа
        hash = self.name2hash(name)
        self.mutex.acquire()    # блокируем поток
        try:
            # address = self.baseAddress + addrOffset
            self.packFrame(hash, address, request, data)
            self.DebugMessage('Sending::frame size: {0}  addr: {1:#x} hash: {2:#x}'.format(len(self.frame), address, hash))
            if not request:
                self.DebugMessage('Sending::data: {}'.format(list(data)))
            self.packRawFrame()
            self.DebugMessage('Sent: {}'.format(self.rawFrame))
            self.serialPort.reset_input_buffer()  # очищаем буфер чтения
            self.serialPort.write(self.rawFrame)
            # ------
            rawFrameRet = self.serialPort.read_until(b'\r')
            # print(type(rawFrame_ret), id(rawFrame_ret))
            rawFrameSize = len(rawFrameRet)
            if rawFrameSize == 0:
                raise OwenProtocolError('OwenProtocolError: No data are received from serial port!')
            self.DebugMessage('Reading::Length: {1} Recieved: {0}'.format(rawFrameRet, rawFrameSize))
            self.unpackRawFrame(rawFrameRet)
            retHash, dataRet = self.unpackFrame()
            if retHash != hash:
                raise OwenProtocolError('OwenProtocolError: Hash mismatch!')
            self.DebugMessage('Reading::data size: {0}'.format(len(data)))
            self.DebugMessage('Reading::data: {0}'.format(list(data)))
        finally:
            self.mutex.release()
        return dataRet

    def getInt16(self, name, address=None):  # возвращает целочисленный параметр
        if address is None:
            address = self.address
        data = self.getPingPong(address, name)
        return self.unpackInt16(data)

    def getChar(self, name, address=None):  # возвращает байт со знаком
        if address is None:
            address = self.address
        data = self.getPingPong(address, name)
        return self.unpackChar(data)

    def getIEEE32(self, name, address=None, withTime=False, withIndex=False):
        if address is None:
            address = self.address
        data = self.getPingPong(address, name)
        return self.unpackIEEE32(data, withTime, withIndex)

    def getFloat24(self, name, address=None):
        if address is None:
            address = self.address
        data = self.getPingPong(address, name)
        return self.unpackFloat24(data)

    def getString(self, name, address=None):  # возвращает строку
        if address is None:
            address = self.address
        data = self.getPingPong(address, name)
        return self.unpackString(data)

    def writeFloat24(self, name, value, address=None):
        data = self.packFloat24(value)
        if address is None:
            address = self.address
        data = self.getPingPong(address, name, request=False, data=data)
        return self.unpackFloat24(data)

    def writeChar(self, name, value, address=None):
        data = self.packChar(value)
        if address is None:
            address = self.address
        data = self.getPingPong(address, name, request=False, data=data)
        return self.unpackChar(data)


class QueueWithPreview(Queue):
    def __init__(self, maxsize=0):
        super().__init__(maxsize)

    def preview(self, block=True, timeout=None):
        """ from Queue.get() """
        with self.not_empty:
            if not block:
                if not self._qsize():
                    raise Empty
            elif timeout is None:
                while not self._qsize():
                    self.not_empty.wait()
            elif timeout < 0:
                raise ValueError("'timeout' must be a non-negative number")
            else:
                endtime = time() + timeout
                while not self._qsize():
                    remaining = endtime - time()
                    if remaining <= 0.0:
                        raise Empty
                    self.not_empty.wait(remaining)
            item = self.queue[0]
            # self.not_full.notify()
            return item

    def putCmd(self, *args):
        try:
            self.put_nowait(args)
        except Full:
            global queueLogMsg
            queueLogMsg.put("Переполнение командной очереди")

# Queue.preview = preview

class OwenDevice(OwenProtocol):
    def __init__(self, serialPort, address, addrLen=8):
        super().__init__(serialPort, address, addrLen)
        self.queueCmd = QueueWithPreview(1)  # очередь из одного элемента
        # self.queueCmd = QueueWithPreview(10)

    def getDeviceName(self, address=None):  # возвращает имя устройства
        return self.getString('dev', address).decode('cp1251')

    def getFirmwareVersion(self, address=None):  # возвращает версию прошивки
        return self.getString('ver', address).decode('cp1251')

    def getNetworkSettings(self, address=None):  # возвращает сетевые параметры прибора
        baudRate = [2400, 4800, 9600, 14400, 19200, 28800, 38400, 57600, 115200][self.getInt16('bps', address)]  # Скорость обмена (бод)
        bits = [7, 8][self.getInt16('Len', address)]  # Длина слова данных (бит)
        parity = ['No', 'EuEn', 'Odd'][self.getInt16('PrtY', address)]  # Состояние бита четности в посылке
        addressLength = [8, 11][self.getInt16('A.Len', address)]  # Длина сетевого адреса (бит)
        baseAddress = self.getInt16('Addr', address)  # Базовый адрес прибора
        stopBits = [1, 2][self.getInt16('sbit', address)]  # Количество стоп-битов в посылке
        errorNumber = self.getInt16('n.Err', address)  # Код сетевой ошибки при последнем обращении к прибору.
        answerDelay = self.getInt16('rSdL', address)  # Задержка ответа от прибора по RS485 (мс)
        return 'Baud rate: {}, Bit length: {}, Parity: {}, Stop bits: {}, ' \
               'Base address: {}, Address length: {}, Last error: {}, ' \
               'Answer delay: {}'.format(baudRate, bits, parity, stopBits, baseAddress, addressLength, errorNumber, answerDelay)