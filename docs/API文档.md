# Gemma4:e4b智能机器人系统API文档

## 1. 认证接口

### 1.1 获取访问令牌

**接口路径**：`POST /api/token`

**功能**：获取访问令牌，用于认证后续请求

**请求参数**：

| 参数名 | 类型 | 必需 | 描述 |
|-------|------|------|------|
| username | string | 是 | 用户名 |
| password | string | 是 | 密码 |

**响应格式**：

```json
{
  "access_token": "string",
  "token_type": "bearer"
}
```

**示例请求**：

```bash
curl -X POST "http://localhost:8000/api/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=alice&password=secret"
```

## 2. 聊天接口

### 2.1 与Gemma4:e4b对话

**接口路径**：`POST /api/chat/gemma4`

**功能**：与Gemma4:e4b模型进行对话

**请求参数**：

| 参数名 | 类型 | 必需 | 描述 |
|-------|------|------|------|
| content | string | 是 | 聊天内容 |
| model | string | 否 | 模型名称，默认为"gemma4:e4b" |
| user_id | string | 否 | 用户ID，默认为"anonymous" |

**响应格式**：

```json
{
  "success": true,
  "content": "string",
  "model": "string",
  "timestamp": "string"
}
```

**示例请求**：

```bash
curl -X POST "http://localhost:8000/api/chat/gemma4" \
  -H "Content-Type: application/json" \
  -d '{"content": "你好，你是谁？", "model": "gemma4:e4b", "user_id": "test_user"}'
```

### 2.2 基于聊天历史对话

**接口路径**：`POST /api/chat/history`

**功能**：基于聊天历史与模型对话

**请求参数**：

| 参数名 | 类型 | 必需 | 描述 |
|-------|------|------|------|
| messages | array | 是 | 聊天历史消息数组 |

**响应格式**：

```json
{
  "success": true,
  "content": "string"
}
```

**示例请求**：

```bash
curl -X POST "http://localhost:8000/api/chat/history" \
  -H "Content-Type: application/json" \
  -d '[{"role": "user", "content": "你好"}, {"role": "assistant", "content": "你好，我是Gemma4智能机器人"}]'
```

## 3. 多模态接口

### 3.1 语音转文本

**接口路径**：`POST /api/audio/transcribe`

**功能**：将语音转换为文本

**请求参数**：

| 参数名 | 类型 | 必需 | 描述 |
|-------|------|------|------|
| audio | file | 是 | 音频文件 |
| model | string | 否 | 模型名称，默认为"base" |

**响应格式**：

```json
{
  "success": true,
  "text": "string"
}
```

**示例请求**：

```bash
curl -X POST "http://localhost:8000/api/audio/transcribe" \
  -H "Content-Type: multipart/form-data" \
  -F "audio=@audio.wav" \
  -F "model=base"
```

### 3.2 文本转语音

**接口路径**：`POST /api/audio/synthesize`

**功能**：将文本转换为语音

**请求参数**：

| 参数名 | 类型 | 必需 | 描述 |
|-------|------|------|------|
| text | string | 是 | 要合成的文本 |
| voice | string | 否 | 语音类型，默认为"default" |

**响应格式**：

```json
{
  "success": true,
  "audio_url": "string"
}
```

**示例请求**：

```bash
curl -X POST "http://localhost:8000/api/audio/synthesize" \
  -H "Content-Type: application/json" \
  -d '{"text": "你好，我是Gemma4智能机器人", "voice": "default"}'
```

### 3.3 图像分析

**接口路径**：`POST /api/vision/analyze`

**功能**：分析图像内容

**请求参数**：

| 参数名 | 类型 | 必需 | 描述 |
|-------|------|------|------|
| image | file | 是 | 图像文件 |
| task | string | 否 | 分析任务，默认为"detect" |

**响应格式**：

```json
{
  "success": true,
  "result": {
    "objects": [
      {
        "name": "string",
        "confidence": 0.95,
        "bbox": [100, 100, 200, 300]
      }
    ],
    "scene": "string",
    "description": "string"
  }
}
```

**示例请求**：

```bash
curl -X POST "http://localhost:8000/api/vision/analyze" \
  -H "Content-Type: multipart/form-data" \
  -F "image=@image.jpg" \
  -F "task=detect"
```

## 4. 学习系统接口

### 4.1 收集用户反馈

**接口路径**：`POST /api/feedback`

**功能**：收集用户对系统的反馈

**请求参数**：

| 参数名 | 类型 | 必需 | 描述 |
|-------|------|------|------|
| user_id | string | 是 | 用户ID |
| item_id | string | 是 | 项目ID |
| feedback_type | string | 是 | 反馈类型 |
| score | integer | 是 | 评分，1-5之间 |
| comment | string | 否 | 评论 |

**响应格式**：

```json
{
  "success": true,
  "message": "反馈收集成功"
}
```

**示例请求**：

```bash
curl -X POST "http://localhost:8000/api/feedback" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test_user", "item_id": "test_item", "feedback_type": "chat", "score": 5, "comment": "测试反馈"}'
```

### 4.2 获取推荐

**接口路径**：`POST /api/recommendations`

**功能**：获取基于用户行为的推荐

**请求参数**：

| 参数名 | 类型 | 必需 | 描述 |
|-------|------|------|------|
| user_id | string | 是 | 用户ID |
| top_n | integer | 否 | 推荐数量，1-20之间，默认为5 |

**响应格式**：

```json
{
  "success": true,
  "recommendations": [
    {
      "action": "string",
      "frequency": 0.8,
      "score": 0.9
    }
  ]
}
```

**示例请求**：

```bash
curl -X POST "http://localhost:8000/api/recommendations" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test_user", "top_n": 5}'
```

### 4.3 系统能力迭代

**接口路径**：`POST /api/iterate`

**功能**：执行系统能力迭代，基于收集的用户行为和反馈

**请求参数**：无

**响应格式**：

```json
{
  "success": true,
  "iteration_result": {
    "updated_knowledge": 10,
    "improved_patterns": 5,
    "execution_time": 2.5
  }
}
```

**示例请求**：

```bash
curl -X POST "http://localhost:8000/api/iterate"
```

## 5. 系统接口

### 5.1 健康检查

**接口路径**：`GET /api/health`

**功能**：检查系统健康状态

**请求参数**：无

**响应格式**：

```json
{
  "success": true,
  "status": "healthy"
}
```

**示例请求**：

```bash
curl -X GET "http://localhost:8000/api/health"
```

### 5.2 获取模型信息

**接口路径**：`GET /api/model/info`

**功能**：获取模型信息

**请求参数**：无

**响应格式**：

```json
{
  "success": true,
  "model_info": {
    "name": "gemma4:e4b",
    "version": "1.0",
    "quantization": "4-bit",
    "memory_usage": "4GB"
  }
}
```

**示例请求**：

```bash
curl -X GET "http://localhost:8000/api/model/info"
```

## 6. 错误响应格式

所有API接口在发生错误时都会返回统一的错误响应格式：

```json
{
  "detail": "错误信息"
}
```

**常见错误码**：

| 状态码 | 描述 |
|-------|------|
| 400 | 请求参数错误 |
| 401 | 未授权 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |
| 503 | 服务不可用 |

## 7. 认证方式

所有需要认证的API接口都需要在请求头中添加`Authorization`字段：

```
Authorization: Bearer <access_token>
```

其中`<access_token>`是通过`/api/token`接口获取的访问令牌。

## 8. 示例代码

### 8.1 Python示例

```python
import requests

# 获取访问令牌
token_response = requests.post(
    "http://localhost:8000/api/token",
    data={"username": "alice", "password": "secret"}
)
token_data = token_response.json()
access_token = token_data["access_token"]

# 与Gemma4:e4b对话
chat_response = requests.post(
    "http://localhost:8000/api/chat/gemma4",
    headers={"Authorization": f"Bearer {access_token}"},
    json={"content": "你好，你是谁？"}
)
chat_data = chat_response.json()
print(chat_data["content"])
```

### 8.2 JavaScript示例

```javascript
// 获取访问令牌
fetch("http://localhost:8000/api/token", {
  method: "POST",
  headers: {
    "Content-Type": "application/x-www-form-urlencoded"
  },
  body: "username=alice&password=secret"
})
.then(response => response.json())
.then(data => {
  const access_token = data.access_token;
  
  // 与Gemma4:e4b对话
  return fetch("http://localhost:8000/api/chat/gemma4", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${access_token}`
    },
    body: JSON.stringify({ content: "你好，你是谁？" })
  });
})
.then(response => response.json())
.then(data => {
  console.log(data.content);
});
```

## 9. 总结

本API文档详细描述了Gemma4:e4b智能机器人系统的所有API接口，包括认证、聊天、多模态、学习系统和系统接口。开发者可以根据文档使用这些接口与系统进行交互，实现各种智能功能。

系统的API设计遵循RESTful风格，使用JSON格式进行数据交换，提供了清晰的错误响应格式和认证机制，确保了API的安全性和可靠性。
