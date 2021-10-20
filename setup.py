import setuptools

# 读取项目的readme介绍
with open("README.md", "r") as fh:
    long_description = fh.read()
setuptools.setup(
    name="SensorsAnalyticsSDK",
    version="1.10.3",
    author="Jianzhong YUE", # 项目作者
    author_email="yuejianzhong@sensorsdata.cn",
    description="This is the official Python SDK for Sensors Analytics.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/sensorsdata/sa-sdk-python",
    packages=setuptools.find_packages(),
)