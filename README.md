# Sensors Analytics

This is the official Python SDK for Sensors Analytics.

## Easy Installation

You can get Sensors Analytics SDK using pip.

```
    pip install SensorsAnalyticsSDK
```

Once the SDK is successfully installed, use the Sensors Analytics SDK likes:

```python
    import sensorsanalytics

    // Gets the url of Sensors Analytics in the home page.
    SA_SERVER_URL = 'YOUR_SERVER_URL'

    // Initialized the Sensors Analytics SDK with Default Consumer
    consumer = sensorsanalytics.DefaultConsumer(SA_SERVER_URL)
    sa = sensorsanalytics.SensorsAnalytics(consumer)

    // Track the event 'ServerStart'
    sa.track("ABCDEFG1234567", "ServerStart")
```

## To learn more

See our [full manual](http://www.sensorsdata.cn/manual/python_sdk.html)
或者加入神策官方 SDK QQ 讨论群：<br><br>
![ QQ 讨论群](https://github.com/sensorsdata/sa-sdk-android/raw/master/docs/qrCode.jpeg)

## License

Copyright 2015－2019 Sensors Data Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

**禁止一切基于神策数据 Python 开源 SDK 的所有商业活动！**