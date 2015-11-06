# coding=utf-8

from __future__ import unicode_literals
import base64
import datetime
import time
import json
import gzip
import re
import threading

try:
    import queue
    import urllib.parse as urllib
    import urllib.request as urllib2
except ImportError:
    import Queue as queue
    import urllib2
    import urllib

SDK_VERSION = '0.1.1'

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


class SensorsAnalytics(object):
    """
    使用一个 SensorsAnalytics 的实例来进行数据发送。
    """

    NAME_PATTERN = re.compile(r"^[a-zA-Z_$][a-zA-Z\d_$]*$")

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

    def __init__(self, consumer=None):
        """
        初始化一个 SensorsAnalytics 的实例。可以选择使用默认的 DefaultConsumer，也可以选择其它的 Consumer 实现。

        已实现的 Consumer 包括:
        DefaultConsumer: 默认实现，逐条、同步的发送数据。
        BatchConsumer: 批量、同步的发送数据。
        AsyncBatchConsumer: 批量、异步的发送数据。
        """
        self._consumer = consumer

    @staticmethod
    def _now():
        return int(time.time() * 1000)

    @staticmethod
    def _json_dumps(data):
        return json.dumps(data, separators=(',', ':'), cls=SensorsAnalytics.DatetimeSerializer)

    def track(self, distinct_id, event_name, properties=None):
        """
        跟踪一个用户的行为。

        :param distinct_id: 用户的唯一标识。
        :param event_name: 事件名称。
        :param properties: 事件的属性。
        """
        event_time = self._extract_user_time(properties) or self._now()
        all_properties = self._get_common_properties()
        if properties:
            all_properties.update(properties)
        data = {
            'type': 'track',
            'event': event_name,
            'time': event_time,
            'distinct_id': distinct_id,
            'properties': all_properties,
        }
        data = self._normalize_data(data)
        self._consumer.send(self._json_dumps(data))

    def track_signup(self, distinct_id, original_id, event_name, properties=None):
        """
        跟踪一个用户的注册行为。

        :param distinct_id: 用户注册之后的唯一标识。
        :param original_id: 用户注册前的唯一标识。
        :param event_name: 事件名称。
        :param properties: 事件的属性。
        """
        event_time = self._extract_user_time(properties) or self._now()
        all_properties = self._get_common_properties()
        if properties:
            all_properties.update(properties)
        data = {
            'type': 'track_signup',
            'event': event_name,
            'time': event_time,
            'distinct_id': distinct_id,
            'original_id': original_id,
            'properties': all_properties,
        }
        data = self._normalize_data(data)
        self._consumer.send(self._json_dumps(data))

    @staticmethod
    def _normalize_data(data):
        # 检查 distinct_id
        if data["distinct_id"] is None or len(str(data['distinct_id'])) == 0:
            raise SensorsAnalyticsIllegalDataException("property [distinct_id] must not be empty")
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

        # 检查 properties
        if "properties" in data and data["properties"] is not None:
            for key, value in data["properties"].items():
                if not is_str(key):
                    raise SensorsAnalyticsIllegalDataException("property key must be a str. [key=%s]" % str(key))
                if not SensorsAnalytics.NAME_PATTERN.match(key):
                    raise SensorsAnalyticsIllegalDataException(
                        "property key must be a valid variable name. [key=%s]" % str(key))

                if not is_str(value) and not is_int(value) and not isinstance(value, float)\
                        and not isinstance(value, datetime.datetime) and not isinstance(value, datetime.date)\
                        and not isinstance(value, list):
                    raise SensorsAnalyticsIllegalDataException(
                        "property value must be a str/int/float/datetime/date/list. [value=%s]" % type(value))
                if isinstance(value, list):
                    for lvalue in value:
                        if not is_str(lvalue):
                            raise SensorsAnalyticsIllegalDataException(
                                "[list] property's value must be a str. [value=%s]" % type(lvalue))

        return data

    @staticmethod
    def _get_common_properties():
        """
        构造所有 Event 通用的属性:
        """
        return {
            '$lib': 'python',
            '$lib_version': SDK_VERSION,
        }

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
        直接设置一个用户的 Profile，如果已存在则覆盖。
        """
        return self._profile_update('profile_set', distinct_id, profiles)

    def profile_increment(self, distinct_id, profiles):
        """
        增减/减少一个用户的某一个或者多个数值类型的 Profile。
        """
        return self._profile_update('profile_increment', distinct_id, profiles)

    def profile_append(self, distinct_id, profiles):
        """
        追加一个用户的某一个或者多个集合类型的 Profile。
        """
        return self._profile_update('profile_append', distinct_id, profiles)

    def profile_unset(self, distinct_id, profile_keys):
        """
        删除一个用户的一个或者多个 Profile。
        """
        if isinstance(profile_keys, list):
            profile_keys = dict((key, True) for key in profile_keys)
        return self._profile_update('profile_unset', distinct_id, profile_keys)

    def profile_delete(self, distinct_id):
        """
        删除整个用户的信息。
        """
        return self._profile_update('profile_delete', distinct_id, {})

    def _profile_update(self, update_type, distinct_id, profiles):
        event_time = self._extract_user_time(profiles) or self._now()
        data = {
            'type': update_type,
            'properties': profiles,
            'time': event_time,
            'distinct_id': distinct_id
        }
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


class DebugConsumer(object):
    """
    调试用的 Consumer，直接输出数据。
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

        def stop(self):
            """
            需要退出时调用此方法，以保证线程安全结束。
            """
            self._stop_event.set()

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

    def sync_flush(self, throw_exception=False):
        """
        执行一次异步发送。 throw_exception 表示在发送失败时是否向外抛出异常。
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
