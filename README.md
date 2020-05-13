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

## 讨论

| 扫码加入神策数据开源社区 QQ 群<br>群号：785122381 | 扫码加入神策数据开源社区微信群 |
| ------ | ------ |
|![ QQ 讨论群](https://opensource.sensorsdata.cn/wp-content/uploads/ContentCommonPic_1.png) | ![ 微信讨论群 ](https://opensource.sensorsdata.cn/wp-content/uploads/ContentCommonPic_2.png) |

## 公众号

| 扫码关注<br>神策数据开源社区 | 扫码关注<br>神策数据开源社区服务号 |
| ------ | ------ |
|![ 微信订阅号 ](https://opensource.sensorsdata.cn/wp-content/uploads/ContentCommonPic_3.png) | ![ 微信服务号 ](https://opensource.sensorsdata.cn/wp-content/uploads/ContentCommonPic_4.png) |


## 新书推荐

| 《数据驱动：从方法到实践》 | 《Android 全埋点解决方案》 | 《iOS 全埋点解决方案》
| ------ | ------ | ------ |
| [![《数据驱动：从方法到实践》](https://opensource.sensorsdata.cn/wp-content/uploads/data_driven_book_1.jpg)](https://item.jd.com/12322322.html) | [![《Android 全埋点解决方案》](https://opensource.sensorsdata.cn/wp-content/uploads/Android-全埋点thumbnail_1.png)](https://item.jd.com/12574672.html) | ![《iOS 全埋点解决方案》](https://opensource.sensorsdata.cn/wp-content/uploads/iOS-全埋点thumbnail_1.png)

## License

Copyright 2015－2020 Sensors Data Inc.

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