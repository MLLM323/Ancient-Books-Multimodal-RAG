from py2neo import Graph, Node, Relationship
import os
import base64
 
# 建立与 Neo4j 的连接
# 修改连接URL，使用正确的bolt端口7687
graph = Graph("bolt://localhost:7687", auth=("neo4j", "tttt"))
 
# 读取本地图片文件
# 使用原始字符串前缀r来避免转义问题
with open(r"nnnnn", "rb") as f:
    image_data = f.read()

# 添加一个简单的测试，确认连接成功
print("Neo4j 连接状态:", graph.service.kernel_version)

# 将二进制图片数据转换为Base64编码字符串
image_base64 = base64.b64encode(image_data).decode('utf-8')

# 创建图片节点
image_node = Node(
    "Image",
    name="皇朝禮器圖式_0_0",
    path=r"D:\ZDM\pythonProject1\zdm\RAG\data\皇朝禮器圖式\0\0.png",
    data=image_base64[:100] + "..."  # 只存储部分数据用于演示
)

# 创建文档节点
document_node = Node(
    "Document",
    name="皇朝禮器圖式",
    description="清代皇家礼器图录"
)

# 创建关系
belongs_to = Relationship(image_node, "BELONGS_TO", document_node)

# 将节点和关系添加到数据库
graph.create(image_node)
graph.create(document_node)
graph.create(belongs_to)

print("已成功将图片节点和文档节点添加到Neo4j数据库")

# 执行查询示例
query_result = graph.run("MATCH (i:Image)-[r:BELONGS_TO]->(d:Document) RETURN i.name, d.name").data()
print("查询结果:", query_result)

# 清理函数 - 如果需要删除测试数据
def cleanup():
    graph.run("MATCH (i:Image {name: '皇朝禮器圖式_0_0'}) DETACH DELETE i")
    graph.run("MATCH (d:Document {name: '皇朝禮器圖式'}) DETACH DELETE d")
    print("已清理测试数据")

# 取消注释下面的行来清理数据
# cleanup()