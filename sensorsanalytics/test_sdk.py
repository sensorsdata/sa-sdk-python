# coding=utf-8

from __future__ import unicode_literals
import unittest

from sdk import *


TEST_URL_PREFIX = 'http://git.sensorsdata.cn/test'
TEST_DEBUG_URL_PREFIX = 'http://10.10.229.134:8001/debug'


class NormalTest(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def gzip_decompress(self, data):
        try:
            return gzip.decompress(data)
        except AttributeError:
            import StringIO

            buf = StringIO.StringIO()
            buf.write(data)
            fd = gzip.GzipFile(fileobj=buf, mode="r")
            fd.rewind()
            value = fd.read()
            fd.close()
            return value

    def mock_request(self, msg):
        if 'data' in msg:
            gzip_data = msg['data']
            data = json.loads(self.gzip_decompress(base64.b64decode(gzip_data)).decode('utf8'))
            data_list = [data]
        else:
            gzip_data = msg['data_list']
            data_list = json.loads(self.gzip_decompress(base64.b64decode(gzip_data)).decode('utf8'))

        for data in data_list:
            self.assertEqual(data['distinct_id'], '1234')
            self.assertTrue(data['time'] is not None)
            self.assertTrue(data['type'] is not None)
            self.assertTrue(isinstance(data['properties'], dict))
            self.msg_counter += 1

    def clear_msg_counter(self):
        self.msg_counter = 0

    def testDebug(self):
        consumer = DebugConsumer(TEST_DEBUG_URL_PREFIX, False)
        sa = SensorsAnalytics(consumer)
        sa.track(1234, 'Test', {'From': 'Baidu'})
        consumer = DebugConsumer(TEST_DEBUG_URL_PREFIX, True)
        sa = SensorsAnalytics(consumer)
        sa.track(1234, 'Test', {'From': 456})
        sa.track(1234, 'Test', {'From': 'Baidu'})

    def testNormal(self):
        consumer = DefaultConsumer(TEST_URL_PREFIX)
        consumer._do_request = self.mock_request
        self.clear_msg_counter()
        sa = SensorsAnalytics(consumer)
        sa.track(1234, 'Test', {'From': 'Baidu'})

        sa.track(1234, 'Test', {'From': 'Baidu', '$time': 1437816376})
        sa.track(1234, 'Test', {'From': 'Baidu', '$time': 1437816376000})
        sa.track(1234, 'Test', {'From': 'Baidu', '$time': '1437816376'})
        sa.track(1234, 'Test', {'From': 'Baidu', '$time': '1437816376000'})
        sa.track(1234, 'Tes123_$t', {'From': 'Baidu', '$time': '1437816376000'})
        sa.track(1234, 'Test', {'From': 'Baidu', '$time': datetime.datetime.now()})

    def testException(self):
        consumer = DefaultConsumer(TEST_URL_PREFIX)
        consumer._do_request = self.mock_request
        self.clear_msg_counter()
        sa = SensorsAnalytics(consumer)

        assertRaisesRegex = None
        if hasattr(self, 'assertRaisesRegex'):
            assertRaisesRegex = self.assertRaisesRegex
        else:
             assertRaisesRegex = self.assertRaisesRegexp

        assertRaisesRegex(SensorsAnalyticsIllegalDataException, "property \[distinct_id\] must not be empty", sa.track, None,
                               'Test', {'From': 'Baidu'})
        assertRaisesRegex(SensorsAnalyticsIllegalDataException, "the max length of property \[distinct_id\] is 255", sa.track, 'abcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyz',
                               'Test', {'From': 'Baidu'})
        assertRaisesRegex(SensorsAnalyticsIllegalDataException, ".*must be a timestamp in microseconds.*",
                               sa.track, 1234, 'Test', {'From': 'Baidu', '$time': 1234})
        assertRaisesRegex(SensorsAnalyticsIllegalDataException, ".*property key must be a valid variable name.*",
                               sa.track, 1234, 'Test', {'From ad': 'Baidu'})
        assertRaisesRegex(SensorsAnalyticsIllegalDataException, ".*property key must be a str.*",
                               sa.track, 1234, 'Test', {123: 'Baidu'})
        assertRaisesRegex(SensorsAnalyticsIllegalDataException, ".*event name must be a valid variable nam.*",
                               sa.track, 1234, 'Test 123', {123: 'Baidu'})
        sa.track(1234, 'Tes123_$t', {'From': 'Baidu', '$time': '1437816376000', 'Test': 1437816376000999933})
        assertRaisesRegex(SensorsAnalyticsIllegalDataException, ".*property value must be a str.*",
                               sa.track, 1234, 'TestEvent', {'TestProperty': {}})
        assertRaisesRegex(SensorsAnalyticsIllegalDataException, ".*property value must be a str.*",
                               sa.track, 1234, 'TestEvent', {'TestProperty': consumer})
        sa.profile_set(1234, {'From': 'Baidu'})
        assertRaisesRegex(SensorsAnalyticsIllegalDataException, ".*property value must be a str.*",
                               sa.profile_set, 1234, {'TestProperty': {}})
        assertRaisesRegex(SensorsAnalyticsIllegalDataException, ".*property's value must be a str.* ",
                               sa.track, 1234, 'TestEvent', {'TestProperty': [123]})
        sa.profile_set(1234, {'From': 'Baidu', 'asd': ["asd", "bbb"]})
        # 'distinct_id' is reserved keyword
        assertRaisesRegex(SensorsAnalyticsIllegalDataException, ".*property key must be a valid variable nam.*",
                               sa.track, 1234, 'TestEvent', {'distincT_id': 'a'})
        # max length is 100
        assertRaisesRegex(SensorsAnalyticsIllegalDataException, ".*property key must be a valid variable nam.*",
                               sa.track, 1234, 'TestEvent', {'a123456789a123456789a123456789a123456789a123456789a123456789a123456789a123456789a123456789a1234567891': 'a'})
        sa.track(1234, 'TestEvent', {'a123456789a123456789a123456789a123456789a123456789a123456789a123456789a123456789a123456789a123456789': 'a'})

    def testDefaultConsumer(self):
        consumer = DefaultConsumer(TEST_URL_PREFIX)
        consumer._do_request = self.mock_request
        self.clear_msg_counter()
        sa = SensorsAnalytics(consumer)
        sa.track('1234', 'Test', {'From': 'Baidu'})
        sa.track_signup('1234', 'abcd', {'Channel': 'Hongbao'})
        sa.profile_delete('1234')
        sa.profile_append('1234', {'Gender': 'Male'})
        sa.profile_increment('1234', {'CardNum': 1})
        sa.profile_set('1234', {'City': '北京'})
        sa.profile_unset('1234', ['City'])
        self.assertEqual(self.msg_counter, 7)

    def testBatchConsumer(self):
        consumer = BatchConsumer(TEST_URL_PREFIX, max_size=5)
        consumer._do_request = self.mock_request
        self.clear_msg_counter()
        sa = SensorsAnalytics(consumer)
        sa.track('1234', 'Test', {'From': 'Baidu'})
        sa.track_signup('1234', 'abcd', {'Channel': 'Hongbao'})
        sa.profile_delete('1234')
        sa.profile_append('1234', {'Gender': 'Male'})
        self.assertEqual(self.msg_counter, 0)
        sa.profile_increment('1234', {'CardNum': 1})
        self.assertEqual(self.msg_counter, 5)
        sa.profile_set('1234', {'City': '北京'})
        sa.profile_unset('1234', ['City'])
        self.assertEqual(self.msg_counter, 5)
        sa.flush()
        self.assertEqual(self.msg_counter, 7)
        sa.close()
        self.assertEqual(self.msg_counter, 7)

    def testAsyncBatchConsumer(self):
        consumer = AsyncBatchConsumer(TEST_URL_PREFIX, flush_max_time=3, flush_size=5)
        consumer._do_request = self.mock_request
        self.clear_msg_counter()
        sa = SensorsAnalytics(consumer)
        sa.track('1234', 'Test', {'From': 'Baidu'})
        sa.track_signup('1234', 'abcd', {'Channel': 'Hongbao'})
        sa.profile_delete('1234')
        sa.profile_append('1234', {'Gender': 'Male'})
        self.assertEqual(self.msg_counter, 0)
        sa.profile_increment('1234', {'CardNum': 1})
        time.sleep(0.1)
        self.assertEqual(self.msg_counter, 5)
        sa.profile_set('1234', {'City': '北京'})
        sa.profile_unset('1234', ['City'])
        self.assertEqual(self.msg_counter, 5)
        sa.flush()
        time.sleep(0.1)
        self.assertEqual(self.msg_counter, 7)
        sa.track('1234', 'Test', {'From': 'Baidu'})
        time.sleep(4)
        self.assertEqual(self.msg_counter, 8)
        sa.track('1234', 'Test', {'From': 'Google'})
        sa.close()
        time.sleep(0.1)
        self.assertEqual(self.msg_counter, 9)


if __name__ == '__main__':
    unittest.main()
