# coding=utf-8

from __future__ import unicode_literals
import base64
import datetime
import time
import json
import gzip
import re
import sys
import threading
import traceback
import logging
import logging.handlers

try:
    from urllib.parse import urlparse
    import queue
    import urllib.parse as urllib
    import urllib.request as urllib2
except ImportError:
    from urlparse import urlparse
    import Queue as queue
    import urllib2
    import urllib

SDK_VERSION = '1.5.3'

try:
    isinstance("", basestring)
    def is_str(s):
        return isinstance(s, basestring)
except NameError:
    def is_str(s):
        return isinstance(s, str)
try:
    isinstance(1, long)
    def is_int(n):
        return isinstance(n, int) or isinstance(n, long)
except NameError:
    def is_int(n):
        return isinstance(n, int)


class SensorsAnalyticsException(Exception):
    pass


class SensorsAnalyticsIllegalDataException(SensorsAnalyticsException):
    """
    在发送的数据格式有误时，SDK会抛出此异常，用户应当捕获并处理。
    """
    pass


class SensorsAnalyticsNetworkException(SensorsAnalyticsException):
    """
    在因为网络或者不可预知的问题导致数据无法发送时，SDK会抛出此异常，用户应当捕获并处理。
    """
    pass


class SensorsAnalyticsDebugException(Exception):
    """
    Debug模式专用的异常
    """
    pass


class SensorsAnalytics(object):
    """
    使用一个 SensorsAnalytics 的实例来进行数据发送。
    """

    NAME_PATTERN = re.compile(r"^((?!^distinct_id$|^original_id$|^time$|^properties$|^id$|^first_id$|^second_id$|^users$|^events$|^event$|^user_id$|^date$|^datetime$)[a-zA-Z_$][a-zA-Z\d_$]{0,99})$", re.I)

    class DatetimeSerializer(json.JSONEncoder):
        """
        实现 date 和 datetime 类型的 JSON 序列化，以符合 SensorsAnalytics 的要求。
        """

        def default(self, obj):
            if isinstance(obj, datetime.datetime):
                head_fmt = "%Y-%m-%d %H:%M:%S"
                return "{main_part}.{ms_part}".format(
                        main_part=obj.strftime(head_fmt),
                        ms_part=int(obj.microsecond/1000))
            elif isinstance(obj, datetime.date):
                fmt = '%Y-%m-%d'
                return obj.strftime(fmt)
            return json.JSONEncoder.default(self, obj)

    def __init__(self, consumer=None, project_name=None, enable_time_free = False):
        """
        初始化一个 SensorsAnalytics 的实例。可以选择使用默认的 DefaultConsumer，也可以选择其它的 Consumer 实现。

        已实现的 Consumer 包括:
        DefaultConsumer: 默认实现，逐条、同步的发送数据;
        BatchConsumer: 批量、同步的发送数据;
        AsyncBatchConsumer: 批量、异步的发送数据;
        DebugConsumer:专门用于调试，逐条、同步地发送数据到专用的Debug接口，并且如果数据有异常会退出并打印异常原因

        @param consumer SDK实例使用的Consumer
        @param project_name Project名称
        @param enable_time_free 打开 time-free 特性
        """
        self._consumer = consumer
        self._default_project_name = project_name
        self._enable_time_free = enable_time_free
        self._super_properties = {}
        self.clear_super_properties();

    @staticmethod
    def _now():
        return int(time.time() * 1000)

    @staticmethod
    def _json_dumps(data):
        return json.dumps(data, separators=(',', ':'), cls=SensorsAnalytics.DatetimeSerializer)

    def register_super_properties(self, super_properties): 
        """
        设置每个事件都带有的一些公共属性，当 track 的 properties 和 super properties 有相同的 key 时，将采用 track 的

        :param super_properties 公共属性
        """
        self._super_properties.update(super_properties)

    def clear_super_properties(self):
        """
        删除所有已设置的事件公共属性
        """
        self._super_properties = {
            '$lib': 'python',
            '$lib_version': SDK_VERSION,
        }

    def track(self, distinct_id, event_name, properties=None):
        """
        跟踪一个用户的行为。

        :param distinct_id: 用户的唯一标识
        :param event_name: 事件名称
        :param properties: 事件的属性
        """
        all_properties = self._super_properties.copy() 
        if properties:
            all_properties.update(properties)
        self._track_event('track', event_name, distinct_id, None, all_properties)
 
    def track_signup(self, distinct_id, original_id, properties=None):
        """
        这个接口是一个较为复杂的功能，请在使用前先阅读相关说明:http://www.sensorsdata.cn/manual/track_signup.html，
        并在必要时联系我们的技术支持人员。

        :param distinct_id: 用户注册之后的唯一标识
        :param original_id: 用户注册前的唯一标识
        :param properties: 事件的属性
        """
        # 检查 original_id
        if original_id is None or len(str(original_id)) == 0:
            raise SensorsAnalyticsIllegalDataException("property [original_id] must not be empty")
        if len(str(original_id)) > 255:
            raise SensorsAnalyticsIllegalDataException("the max length of property [original_id] is 255")
       
        all_properties = self._super_properties.copy() 
        if properties:
            all_properties.update(properties)
        
        self._track_event('track_signup', '$SignUp', distinct_id, original_id, all_properties)

    @staticmethod
    def _normalize_data(data):
        # 检查 distinct_id
        if data["distinct_id"] is None or len(str(data['distinct_id'])) == 0:
            raise SensorsAnalyticsIllegalDataException("property [distinct_id] must not be empty")
        if len(str(data['distinct_id'])) > 255:
            raise SensorsAnalyticsIllegalDataException("the max length of property [distinct_id] is 255")
        data['distinct_id'] = str(data['distinct_id'])

        # 检查 time
        if isinstance(data['time'], datetime.datetime):
            data['time'] = time.mktime(data['time'].timetuple()) * 1000 + data['time'].microsecond / 1000

        ts = int(data['time'])
        ts_num = len(str(ts))
        if ts_num < 10 or ts_num > 13:
                raise SensorsAnalyticsIllegalDataException("property [time] must be a timestamp in microseconds")

        if ts_num == 10:
            ts *= 1000
        data['time'] = ts

        # 检查 Event Name
        if 'event' in data and not SensorsAnalytics.NAME_PATTERN.match(data['event']):
            raise SensorsAnalyticsIllegalDataException("event name must be a valid variable name. [name=%s]" % data['event'])

        # 检查 Event Name
        if 'project' in data and not SensorsAnalytics.NAME_PATTERN.match(data['project']):
            raise SensorsAnalyticsIllegalDataException("project name must be a valid variable name. [project=%s]" % data['project'])

        # 检查 properties
        if "properties" in data and data["properties"] is not None:
            for key, value in data["properties"].items():
                if not is_str(key):
                    raise SensorsAnalyticsIllegalDataException("property key must be a str. [key=%s]" % str(key))
                if len(key) > 255:
                    raise SensorsAnalyticsIllegalDataException("the max length of property key is 256. [key=%s]" % str(key))
                if not SensorsAnalytics.NAME_PATTERN.match(key):
                    raise SensorsAnalyticsIllegalDataException(
                        "property key must be a valid variable name. [key=%s]" % str(key))

                if is_str(value) and len(value) > 8191:
                    raise SensorsAnalyticsIllegalDataException("the max length of property key is 8192. [key=%s]" % str(key))

                if not is_str(value) and not is_int(value) and not isinstance(value, float)\
                        and not isinstance(value, datetime.datetime) and not isinstance(value, datetime.date)\
                        and not isinstance(value, list) and value is not None:
                    raise SensorsAnalyticsIllegalDataException(
                        "property value must be a str/int/float/datetime/date/list. [value=%s]" % type(value))
                if isinstance(value, list):
                    for lvalue in value:
                        if not is_str(lvalue):
                            raise SensorsAnalyticsIllegalDataException(
                                "[list] property's value must be a str. [value=%s]" % type(lvalue))

        return data

    def _get_lib_properties(self):
        lib_properties = {
            '$lib' : 'python',
            '$lib_version' : SDK_VERSION,
            '$lib_method' : 'code',
        }

        if '$app_version' in self._super_properties: 
            lib_properties['$app_version'] = self._super_properties['$app_version']

        try:
            raise Exception
        except:
            trace = traceback.extract_stack()
            if len(trace) > 3:
                file_name = trace[-4][0]
                line_number = trace[-4][1]
                
                if trace[-4][2].startswith('<'):
                    function_name = ''
                else:
                    function_name = trace[-4][2]
                
                if len(trace) > 4 and trace[-5][3]:
                    class_name = trace[-5][3].split('(')[0] 
                else:
                    class_name = ''

                lib_properties['$lib_detail'] = '%s##%s##%s##%s' % (class_name, function_name, file_name, line_number) 

        return lib_properties

    def _get_common_properties(self):
        """
        构造所有 Event 通用的属性:
        """
        common_properties = {
            '$lib': 'python',
            '$lib_version': SDK_VERSION,
        }

        if self._app_version:
            common_properties['$app_version'] = self._app_version

        return common_properties


    @staticmethod
    def _extract_user_time(properties):
        """
        如果用户传入了 $time 字段，则不使用当前时间。
        """
        if properties is not None and '$time' in properties:
            t = properties['$time']
            del (properties['$time'])
            return t
        return None

    def profile_set(self, distinct_id, profiles):
        """
        直接设置一个用户的 Profile，如果已存在则覆盖

        :param distinct_id: 用户的唯一标识
        :param profiles: 用户属性
        """
        return self._track_event('profile_set', None, distinct_id, None, profiles)

    def profile_set_once(self, distinct_id, profiles):
        """
        直接设置一个用户的 Profile，如果某个 Profile 已存在则不设置。

        :param distinct_id: 用户的唯一标识
        :param profiles: 用户属性
        """
        return self._track_event('profile_set_once', None, distinct_id,  None, profiles)

    def profile_increment(self, distinct_id, profiles):
        """
        增减/减少一个用户的某一个或者多个数值类型的 Profile。

        :param distinct_id: 用户的唯一标识
        :param profiles: 用户属性
        """
        return self._track_event('profile_increment', None, distinct_id,  None, profiles)

    def profile_append(self, distinct_id, profiles):
        """
        追加一个用户的某一个或者多个集合类型的 Profile。

        :param distinct_id: 用户的唯一标识
        :param profiles: 用户属性
        """
        return self._track_event('profile_append', None, distinct_id, None, profiles)

    def profile_unset(self, distinct_id, profile_keys):
        """
        删除一个用户的一个或者多个 Profile。

        :param distinct_id: 用户的唯一标识
        :param profile_keys: 用户属性键值列表
        """
        if isinstance(profile_keys, list):
            profile_keys = dict((key, True) for key in profile_keys)
        return self._track_event('profile_unset', None, distinct_id, None, profile_keys)

    def profile_delete(self, distinct_id):
        """
        删除整个用户的信息。

        :param distinct_id: 用户的唯一标识
        """
        return self._track_event('profile_delete', None, distinct_id, None, {})

    def _track_event(self, event_type, event_name, distinct_id, original_id, properties):
        event_time = self._extract_user_time(properties) or self._now()

        data = {
            'type': event_type,
            'time': event_time,
            'distinct_id': distinct_id,
            'properties': properties,
            'lib': self._get_lib_properties(),
        }
        if self._default_project_name is not None:
            data['project'] = self._default_project_name

        if event_type == "track" or event_type == "track_signup":
            data["event"] = event_name

        if event_type == "track_signup":
            data["original_id"] = original_id

        if self._enable_time_free:
            data["time_free"] = True

        data = self._normalize_data(data)
        self._consumer.send(self._json_dumps(data))

    def flush(self):
        """
        对于不立即发送数据的 Consumer，调用此接口应当立即进行已有数据的发送。
        """
        self._consumer.flush()

    def close(self):
        """
        在进程结束或者数据发送完成时，应当调用此接口，以保证所有数据被发送完毕。
        如果发生意外，此方法将抛出异常。
        """
        self._consumer.close()

class DefaultConsumer(object):
    """
    默认的 Consumer实现，逐条、同步的发送数据给接收服务器。
    """

    def __init__(self, url_prefix, request_timeout=None):
        """
        初始化 Consumer。

        :param url_prefix: 服务器的 URL 地址。
        :param request_timeout: 请求的超时时间，单位毫秒。
        """
        self._url_prefix = url_prefix
        self._request_timeout = request_timeout

    @staticmethod
    def _gzip_string(data):
        try:
            return gzip.compress(data)
        except AttributeError:
            import StringIO

            buf = StringIO.StringIO()
            fd = gzip.GzipFile(fileobj=buf, mode="w")
            fd.write(data)
            fd.close()
            return buf.getvalue()

    def _do_request(self, data):
        """
        使用 urllib 发送数据给服务器，如果发生错误会抛出异常。
        """
        encoded_data = urllib.urlencode(data).encode('utf8')
        try:
            request = urllib2.Request(self._url_prefix, encoded_data)

            if self._request_timeout is not None:
                urllib2.urlopen(request, timeout=self._request_timeout)
            else:
                urllib2.urlopen(request)
        except urllib2.HTTPError as e:
            raise SensorsAnalyticsNetworkException(e)
        return True

    def send(self, msg):
        return self._do_request({
            'data': self._encode_msg(msg),
            'gzip': 1
        })

    def _encode_msg(self, msg):
        return base64.b64encode(self._gzip_string(msg.encode('utf8')))

    def _encode_msg_list(self, msg_list):
        return base64.b64encode(self._gzip_string(('[' + ','.join(msg_list) + ']').encode('utf8')))

    def flush(self):
        pass

    def close(self):
        pass


class BatchConsumer(DefaultConsumer):
    """
    批量发送数据的 Consumer，当且仅当数据达到 max_size 参数指定的量时，才将数据进行发送。
    """

    def __init__(self, url_prefix, max_size=50, request_timeout=None):
        """
        初始化 BatchConsumer。

        :param url_prefix: 服务器的 URL 地址。
        :param max_size: 批量发送的阈值。
        :param request_timeout: 请求服务器的超时时间，单位毫秒。
        :return:
        """
        super(BatchConsumer, self).__init__(url_prefix, request_timeout)
        self._buffers = []
        self._max_size = min(50, max_size)

    def send(self, json_message):
        self._buffers.append(json_message)
        if len(self._buffers) >= self._max_size:
            self.flush()

    def flush(self):
        """
        用户可以主动调用 flush 接口，以便在需要的时候立即进行数据发送。
        """
        while self._buffers:
            msg_list = self._buffers[:self._max_size]
            self._do_request({
                'data_list': self._encode_msg_list(msg_list),
                'gzip': 1
            })
            self._buffers = self._buffers[self._max_size:]

    def close(self):
        """
        在发送完成时，调用此接口以保证数据发送完成。
        """
        self.flush()


class AsyncBatchConsumer(DefaultConsumer):
    """
    异步、批量发送数据的 Consumer。使用独立的线程进行数据发送，当满足以下两个条件之一时进行数据发送:
    1. 数据条数大于预定义的最大值
    2. 数据发送间隔超过预定义的最大时间
    """

    class AsyncFlushThread(threading.Thread):
        """
        发送数据的独立线程，在这里执行实际的网络请求。
        """

        def __init__(self, consumer):
            super(AsyncBatchConsumer.AsyncFlushThread, self).__init__()
            self._consumer = consumer
            # 用于实现安全退出
            self._stop_event = threading.Event()
            self._finished_event = threading.Event()

        def stop(self):
            """
            需要退出时调用此方法，以保证线程安全结束。
            """
            self._stop_event.set()
            self._finished_event.wait()

        def run(self):
            while True:
                # 如果 need_flush 标志位为 True，或者等待超过 flush_max_time，则继续执行
                self._consumer.need_flush.wait(self._consumer.flush_max_time)
                # 进行发送，如果成功则清除标志位
                if self._consumer.sync_flush():
                    self._consumer.need_flush.clear()
                # 发现 stop 标志位时安全退出
                if self._stop_event.isSet():
                    break
            self._finished_event.set()

    def __init__(self, url_prefix, flush_max_time=3, flush_size=20,
                 max_batch_size=100, max_size=1000, request_timeout=None):
        """
        初始化 AsyncBatchConsumer。

        :param url_prefix: 服务器的 URL 地址。
        :param flush_max_time: 两次发送的最大间隔时间，单位秒。
        :param flush_size: 队列缓存的阈值，超过此值将立即进行发送。
        :param max_batch_size: 单个请求发送的最大大小。
        :param max_size: 整个缓存队列的最大大小。
        :param request_timeout: 请求的超时时间，单位毫秒。
        """
        super(AsyncBatchConsumer, self).__init__(url_prefix, request_timeout)

        self._flush_size = flush_size
        self.flush_max_time = flush_max_time
        self._max_batch_size = max_batch_size

        self._queue = queue.Queue(max_size)

        # 用于通知刷新线程应当立即进行刷新
        self.need_flush = threading.Event()
        self._flush_buffer = []

        # 初始化发送线程，并设置为 Daemon 模式
        self._flushing_thread = AsyncBatchConsumer.AsyncFlushThread(self)
        self._flushing_thread.daemon = True
        self._flushing_thread.start()

    def send(self, json_message):
        # 这里不进行实际的发送，而是向队列里插入。如果队列已满，则抛出异常。
        try:
            self._queue.put_nowait(json_message)
        except queue.Full as e:
            raise SensorsAnalyticsNetworkException(e)

        if self._queue.qsize() >= self._flush_size:
            self.need_flush.set()

    def flush(self):
        self.need_flush.set()

    def sync_flush(self, throw_exception=True):
        """
        执行一次同步发送。 throw_exception 表示在发送失败时是否向外抛出异常。
        """
        flush_success = False

        if len(self._flush_buffer) == 0:
            for i in range(self._max_batch_size):
                if not self._queue.empty():
                    self._flush_buffer.append(self._queue.get_nowait())
                else:
                    break

        if len(self._flush_buffer) > 0:
            try:
                self._do_request({
                    'data_list': self._encode_msg_list(self._flush_buffer),
                    'gzip': 1
                })
                flush_success = True
                self._flush_buffer = []
            except SensorsAnalytics as e:
                if throw_exception:
                    raise e
        return flush_success

    def close(self):
        # 关闭时首先停止发送线程
        self._flushing_thread.stop()
        # 循环发送，直到队列和发送缓存都为空
        while not self._queue.empty() or not len(self._flush_buffer) == 0:
            self.sync_flush(True)


class DebugConsumer(object):
    """
    调试用的 Consumer，逐条发送数据到服务器的Debug API,并且等待服务器返回的结果
    具体的说明在http://www.sensorsdata.cn/manual/
    """

    def __init__(self, url_prefix, write_data=True, request_timeout=None):
        """
        初始化Consumer
        :param url_prefix: 服务器提供的用于Debug的API的URL地址,特别注意,它与导入数据的API并不是同一个
        :param write_data: 发送过去的数据,是真正写入,还是仅仅进行检查
        :param request_timeout:请求的超时时间,单位毫秒
        :return:
        """
        debug_url = urlparse(url_prefix)
        ## 将 URI Path 替换成 Debug 模式的 '/debug'
        debug_url = debug_url._replace(path = '/debug')
        
        self._debug_url_prefix = debug_url.geturl()
        self._request_timeout = request_timeout
        self._debug_write_data = write_data

    @staticmethod
    def _gzip_string(data):
        try:
            return gzip.compress(data)
        except AttributeError:
            import StringIO

            buf = StringIO.StringIO()
            fd = gzip.GzipFile(fileobj=buf, mode="w")
            fd.write(data)
            fd.close()
            return buf.getvalue()

    def _do_request(self, data):
        """
        使用 urllib 发送数据给服务器，如果发生错误会抛出异常。
        response的结果,会返回
        """
        encoded_data = urllib.urlencode(data).encode('utf8')
        try:
            request = urllib2.Request(self._debug_url_prefix, encoded_data)
            if not self._debug_write_data:      # 说明只检查,不真正写入数据
                request.add_header('Dry-Run', 'true')
            if self._request_timeout is not None:
                response = urllib2.urlopen(request, timeout=self._request_timeout)
            else:
                response = urllib2.urlopen(request)
        except urllib2.HTTPError as e:
            return e
        return response

    def send(self, msg):
        response = self._do_request({
            'data': self._encode_msg(msg),
            'gzip': 1
        })
        print('==========================================================================')
        ret_code = response.code
        if ret_code == 200:
            print('valid message: %s' % msg)
        else:
            print('invalid message: %s' % msg)
            print('ret_code: %s' % ret_code)
            print('ret_content: %s' % response.read().decode('utf8'))
        if ret_code >= 300:
            raise SensorsAnalyticsDebugException()

    def _encode_msg(self, msg):
        return base64.b64encode(self._gzip_string(msg.encode('utf8')))

    def flush(self):
        pass

    def close(self):
        pass


class ConsoleConsumer(object):
    """
    将数据直接输出到标准输出
    """

    def __init__(self):
        pass

    @staticmethod
    def send(msg):
        print(msg)

    def flush(self):
        pass

    def close(self):
        pass


class LoggingConsumer(object):
    """
    将数据使用 logging 库输出到指定路径，并默认按天切割
    """

    def __init__(self, prefix, backupCount=0, when='midnight'):
        log_handler = logging.handlers.TimedRotatingFileHandler(prefix, when=when, backupCount=backupCount)
        log_handler.setFormatter(logging.Formatter('%(message)s'))
        self.logger = logging.getLogger('SensorsAnalyticsLogger')
        self.logger.propagate = False
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(log_handler)

    def send(self, msg):
        self.logger.info(msg)

    def flush(self):
        self.logger.handlers[0].flush()

    def close(self):
        self.logger.handlers[0].close()
