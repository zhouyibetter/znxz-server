# 大模型接口工具类使用说明
目前只简单实现了非流式输出的大模型工具类，使用示例如下：
```python
from Utils.llm_api import LlmApi

llm = LlmApi()
resp = llm.znxz("你是什么模型？")
```
等待几秒后你就会得到大模型的回答。