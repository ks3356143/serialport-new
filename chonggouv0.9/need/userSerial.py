# -*- coding: utf-8 -*-
import sys
from time import sleep
import copy

import serial
from serial import Serial
from serial.serialutil import *
from serial.tools import list_ports

import threading
import struct

from PyQt5.QtCore import pyqtSignal,QObject

#删除print调试
# def print(*args, **kwargs):
#     pass
# 调试相关功能定义
import logging
LOG_FORMAT = "%(asctime)s>%(levelname)s>PID:%(process)d %(thread)d>%(module)s>%(funcName)s>%(lineno)d>%(message)s"
logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT, )
# 是否打印调试信息标志
debug = True
# 接收线程中轮询周期 单位秒
rcvPeriod = 0.01
# 接收线程缓存最大值
rcvBuffMaxLen = 1024*1024*50
# 波特率列表
suportBandRateList = (300, 600, 1200, 2400, 4800, 9600, 14400, 19200, 38400, 56000, 57600, 115200, 230400, 460800, 500000, 576000, 921600, 1000000, 1152000, 1500000, 2000000, 2500000, 3000000, 3500000, 4000000)
# 固定接收位数
fixedRcvcount = 240
# 常量，系统特性
if debug == True:
    logging.debug("pyserial版本:{}".format(serial.VERSION))#pyserial版本
    logging.debug("可用波特率:{}".format(suportBandRateList))
    # logging.debug(""(serial.device(0))#串口号与设备名称转换 0--COM1 1-COM2
    # logging.debug("可用波特率:{}".format(Serial.BAUDRATES))
    logging.debug("可用数据位:{}".format(Serial.BAUDRATES))
    logging.debug("可用校验类型:{}".format(Serial.PARITIES))
    logging.debug("可用停止位:{}".format(Serial.STOPBITS))
# 定义传输过来数据帧头2字节，类型位1字节
STX1 = 0xE1 #不需要b
STX2 = 0x16 #定义协议中帧头2字节
XXL1 = 0x22 #类型编码
XXLG = 0xFF #广播命令字

class userSerial(QObject):
    """
    userSerial类封装了一个serial对象，并对serial对象进行了优化处理
    当接收到数据时触发signalRcv
    当接收异常时触发signalRcvError
    示例
        import userSerial
        sndBuf = bytes(1,2,3,4,5,6)
        com = userSerial(bandrate=9600)
        com.open("com1")
        com.send(sndBuf)
        rcvBuf = com.recv(n)
        com.close()
    """
    # 定义接收信号 当接收到数据时发射此信号,信号带着接收数量给UI显示
    signalRcv = pyqtSignal(int)
    # 定义接收异常信号 当接收到数据时发射此信号
    signalRcvError = pyqtSignal(str)
    # 定义接收信号，信号带着data_dict给UI处理
    signalRcvdata = pyqtSignal(dict)
    # 定义广播消息接收信号，信号带着list给UI处理
    signalguangbo = pyqtSignal(list)
    #初始化串口
    def __init__(self, baudrate=115200, bytesize=EIGHTBITS, 
                    parity=PARITY_ODD, stopbits=STOPBITS_ONE, 
                    timeout=None,writetimeout = None, rtscts=False,xonxoff=False):
        # 实例化一个标准Serial对象
        super().__init__()
        self.port = Serial()
        if debug == True:
            logging.debug("初始化串口对象")

        #定义接收相关数据
        self.RcvBuff = bytearray()#接收缓存
        self.RcvBuffLock = threading.RLock()#接收缓存访问递归锁
        #初始化串口
        try:
            self.port.baudrate = baudrate
            self.port.bytesize = bytesize
            self.port.parity = parity
            self.port.stopbits =  stopbits
            self.port.timeout = timeout
            self.port.writeTimeout = writetimeout
            self.port.rtscts = rtscts
            if rtscts == True:
                self.port.xonxoff = False
            else:
                self.port.xonxoff = xonxoff
        except Exception as e:
            if debug == True:
                logging.error("初始化串口失败:{}".format(e))
            raise Exception(e)

    @classmethod
    def getPortsList(cls):
        """
        获取系统端口列表
        :return:可用端口列表
        """
        if debug == True:
            logging.debug("开始扫描可用串口:")
        portsList = []
        # 获取可用端口号
        ports = list(list_ports.comports())
        # 按字母顺序排序并遍历
        for i in sorted(ports):
            com, name = str(i).split('-',1)
            # 删除前后空格
            com = com.strip(" ")
            name = name.strip(" ")
            # 将端口号及名称添加到列表
            portsList.append((com,name))
        if debug == True:
            logging.debug("扫描结束,可用串口:{}".format(portsList))
        return portsList #返回列表

    def open(self,port):
        """
        传入port号，打开串口 成功打开后开启接收线程
        :param port:com1 com2等类似名称
        :return:
        """
        try:
            if (self.port.isOpen() == False):
                self.port.setPort(port)
                self.port.open()
            else:
                if debug == True:
                    logging.warning("{}-已被打开{}".format(port))
        except Exception as e:
            if debug == True:
                logging.warning("{}-无法打开{}".format(port,e))
            raise Exception(e)
        # 当端口已被打开时执行
        if (self.port.isOpen() ==True):
            if debug == True:
                logging.debug("{}-打开".format(1))
            # 清除缓冲区
            self.RcvBuffLock.acquire()
            self.RcvBuff.clear()
            self.RcvBuffLock.release()
            # 开启接收线程
            threading.Thread(target=self.recvHandle, args=(),daemon=True).start()
            if debug == True:
                logging.debug("开启接收线程")

    def close(self):
        """
        关闭串口
        :return:
        """
        if self.port.isOpen():
            self.port.close()
            if debug == True:
                logging.debug("{}-已关闭***********".format(self.port.name))
            self.RcvBuffLock.acquire()
            self.RcvBuff.clear()
            self.RcvBuffLock.release()
        return

    def getPortState(self):
        """
        获取端口状态
        :return: True if port is open
                False if port is close
        """
        return self.port.isOpen()

    def getRcvCount(self):
        """
        获取已接收数据量 可用于轮询模式
        """
        if self.port.isOpen():
            self.RcvBuffLock.acquire()
            count = len(self.RcvBuff)
            self.RcvBuffLock.release()
            return count
        else:
            return 0

    def getSndCount(self):
        """
        获取待发送数据量
        """
        if self.port.isOpen():
            return self.port.out_waiting
        else:
            return 0

    def send(self, bytesBuf):
        """
        发送函数
        """
        if self.port.isOpen():
            try:
                sndOkCnt = self.port.write(bytes(bytesBuf))
                # 打印发送数据 bytes类型
                if debug == True:
                    logging.debug("Send:{} {}".format(sndOkCnt, bytesBuf))
                return
            except SerialTimeoutException as e:
                if debug == True:
                    logging.error("Send失败-SerialTimeoutException:{}".format(e))
            except SerialException as e:
                if debug == True:
                    logging.error("Send失败-SerialException:{}".format(e))
            except Exception as e:
                if debug == True:
                    logging.error("Send失败-Exception:{}".format(e))
            finally:
                return 0
        else:
            return 0

    def send_order(self, bytesBuf):
        """
        发送生成指令的函数
        """
        if self.port.isOpen():
            try:
                sndOkCnt = self.port.write(bytes(bytesBuf))
                # 打印发送数据 bytes类型
                if debug == True:
                    logging.debug("Send:{} {}".format(sndOkCnt, bytesBuf))
                return
            except SerialTimeoutException as e:
                if debug == True:
                    logging.error("Send失败-SerialTimeoutException:{}".format(e))
            except SerialException as e:
                if debug == True:
                    logging.error("Send失败-SerialException:{}".format(e))
            except Exception as e:
                if debug == True:
                    logging.error("Send失败-Exception:{}".format(e))
            finally:
                return 0
        else:
            return 0
        

    def recv(self,count):
        """
        接收函数
        从本地缓冲中读取数据（并非直接从串口缓冲中取数）
        bytesBuf = userSerial.recv(cnt)
        count:期望读取的数据量
            当count<=当前缓冲中数量时，len(bytesBuf) = cnt
            当count> 当前缓冲中数量时，len(bytesBuf) = len(缓冲)
        return:是bytes型对象
        """
        if len(self.RcvBuff) >= count:
            # 截取部分缓冲中数据
            self.RcvBuffLock.acquire()
            buf = self.RcvBuff[:count]
            print('!!!!!!!!!!!!!!目前缓存是!!!!!',len(self.RcvBuff))
            self.RcvBuff = self.RcvBuff[count:]
            self.RcvBuff.clear() #添加删除缓存操作
            self.RcvBuffLock.release()
            print('!!!!!!!!!!!!!!目前取后缓存是!!!!!!',len(self.RcvBuff))
        elif len(self.RcvBuff):
            # 将全部缓冲中数据返回
            self.RcvBuffLock.acquire()
            buf = copy.deepcopy(self.RcvBuff)
            self.RcvBuff.clear()
            self.RcvBuffLock.release()
        else:
            buf = bytes()
        return buf

    def recvHandle(self):
        """
        接收线程
            用于将周期性查询串口设备接收状态并将硬件串口设备接收到的数据转存到本地接收缓冲self.RcvBuff中
            此线程函数在打开串口时启动
        :return:
        """
        start = 0
        stop = 0
        if debug == True:
            logging.debug("接收线程已启动")
        while (self.port.isOpen()):
            try:
                count = self.port.in_waiting
                if count >= fixedRcvcount:
                    self.RcvBuffLock.acquire()
                    rcv = self.port.read(count)
                    self.RcvBuff += rcv
                    #如果缓存数据超长 截取最新部分
                    if len(self.RcvBuff) > rcvBuffMaxLen:
                        self.RcvBuff = self.RcvBuff[len(self.RcvBuff)-rcvBuffMaxLen:]
                    self.RcvBuffLock.release()

                    if debug == True:
                        # 以16进制形式打印接收到的数据,变成了大写字符串
                        logging.debug("接收16进制:{}B,数据为:{}".format(count, "".join(["{:02X}".format(i) for i in rcv])))

                    recv_data = self.jiequshuju()
                    if recv_data != None:
                        data_dict = {} #定义一个dict来放入数据，@@@@@@@@@@注意看下这个是否ok，还是放前面去
                        print('最后截取到的数据为:',recv_data)
                        print('最后截取到的数据长度为:',len(recv_data))
                        #把recv_data转化为str，用于截取
                        recv_data_str = "".join(["{:02X}".format(i) for i in recv_data]) #重点！！！
                        print('转化为字符串后的获取的数据:',recv_data_str,'长度为:',len(recv_data_str)) #测试数据为48

                        #以下为取有用数据，计数jishu=0，没取到一个加1，遇到截取完了后退出循环
                        index_changdu = '' #初始化长度
                        index_len = 0 #一个变量的数据的长度
                        index = 0
                        while index < len(recv_data_str):
                            index_changdu = recv_data_str[index + 8:index + 10] #数据长度获取，因为地址8个字符长度位2个字符固定
                            index_len = int(index_changdu,16)
                            #去地址8个字符，通过index来取
                            data_dict[recv_data_str[index :index + 8]] = recv_data_str[index + 10:index + 10 + index_len*2]
                            index = index + 10 + index_len*2
                        print('获取到的dict为~~~~',data_dict)
                        self.signalRcvdata.emit(data_dict)
                # 发送当前接收到的数据量
                    self.signalRcv.emit(count)
            except SerialException as e:
                self.signalRcvError.emit(e.args[0])
                if debug == True:
                    logging.error("接收失败-SerialException:{}".format(e))
                self.close()
            except Exception as e:
                self.signalRcvError.emit(e.args[0])
                if debug == True:
                    logging.error("接收失败-Exception:{}".format(e))
                self.close()
            finally:
                pass
            # 睡眠
            sleep(rcvPeriod)
        if debug == True:
            logging.debug("端口关闭，接收线程已结束")  

    def jiequshuju(self):
        bytebuf = self.recv(fixedRcvcount)
        print('现在目前缓存是',len(self.RcvBuff))
        recv_msg = [] #储存提取出的数值
        length = 0 #数据长度，最大0xFA
        if bytebuf[0] == STX1:
            print('检验帧头第一位成功！！！')
            if bytebuf[1] == STX2:
                print('校验帧头第二位成功！！！')
                if bytebuf[3] == XXL1:
                    print('类型码校验成功！！！')
                    length = bytebuf[2] #取出有效数据长度,测试数据位24个,那么我就取24个字节放进去
                    print('取出的有效数据长度为:',length) 
                    #得到length后直接取出有效数据位和校验和
                    recv_msg = bytebuf[4:length+4]
                    print('程序截取的数据位：',recv_msg,len(recv_msg))
                    #检验校验和
                    if (True == self.uart_jiaoyan(recv_msg,bytebuf[-2:],length)):
                        return recv_msg
                    else:
                        return None
                    
                if bytebuf[3] == XXLG:
                    print('这是广播消息！！！')
                    length = bytebuf[2] #取出广播消息有效数据长度
                    print("取出有效数据长度：",length) #广播消息固定为5
                    recv_msg = bytebuf[4:length+4]
                    print('广播消息的数据为',recv_msg,len(recv_msg))
                    #检验校验和
                    if (True == self.uart_jiaoyan(recv_msg,bytebuf[-2:],length)):
                        self.guangbomsg(recv_msg)
                    else:
                        pass

    def uart_jiaoyan(self,recv_msg,hou2,length):
        check_sum = 0 #校验和
        for i in range(length): #lenth加上帧头2字节和长度位1字节
            check_sum += recv_msg[i]
        check_sum &= 0xFFFF
        print('识别的校验和为：',check_sum)
        hou2_sum = struct.unpack('>H',hou2)[0]
        print('后2个字节的和为：',hou2_sum)
        if check_sum == hou2_sum:
            return True
        else:
            return False

    #广播消息的处理函数
    def guangbomsg(self,recv_data):
        if recv_data:
            print('广播消息校验和OKOKOKOK')
        else:
            print('广播消息校验和错误！！！！！！！')
        if recv_data != None:
            data_broadcast = [] #定义list放入数据,
            print('最后广播消息数据为：',recv_data)
            print('广播消息长度为',len(recv_data))
            #转化为str用于解析
            recv_data_str = "".join(["{:02X}".format(i) for i in recv_data]) 
            print('转化为字符串后的获取的数据:',recv_data_str,'长度为:',len(recv_data_str))
            #去掉前4个字节，也就是8个字符
            # recv_data_str = recv_data_str[8:]
            if len(recv_data_str) == 10:
                data_broadcast.append(recv_data_str[:2])  #请求阶段0x44、0x33、0x55、0x66、
                data_broadcast.append(recv_data_str[2:4]) #完成状态0或者1
                data_broadcast.append(recv_data_str[4:8]) #丢失帧号
                data_broadcast.append(recv_data_str[8:10]) #丢失帧号
            print("底层截取到的广播数组为:",data_broadcast)
            #发送数组数据
            self.signalguangbo.emit(data_broadcast)
            #发送收到数据量
            self.signalRcv.emit(len(recv_data))
            
            
          
                    
            
        

    def flush(self):
        """
        清除串口缓冲区
        :return:
        """
        try:
            if self.port.isOpen():
                # 缓冲管理
                self.port.flush()
                # 清除接收缓存
                self.RcvBuffLock.acquire()
                self.RcvBuff.clear()
                self.RcvBuffLock.release()
                if debug == True:
                    logging.error("flush成功")
        except SerialException as e:
            if debug == True:
                logging.error("flush-SerialException:{}".format(e))
        except Exception as e:
            if debug == True:
                logging.error("flush-Exception:{}".format(e))
        finally:
            pass