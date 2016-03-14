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

