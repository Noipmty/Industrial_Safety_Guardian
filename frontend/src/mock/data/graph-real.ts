import type { GraphData } from '@/types'

/**
 * 真实知识图谱数据 —— 由后端接口实际返回生成（非手编 mock）：
 * GET /api/v1/admin/graph/overview?limit=150
 * 数据源：Neo4j（GraphRAG 流水线 Entity / REL / Community），生成日期 2026-10-12。
 * 全图统计：2840 实体 / 3850 关系 / 223 社区。
 * 本文件为「度数最高的 150 个实体」构成的概览子图（376 条边）。
 */
export const REAL_GRAPH: GraphData = {
  anchors: [],
  nodes: [
  {
    "id": "有限空间作业",
    "name": "有限空间作业",
    "entityType": "作业类型",
    "degree": 195
  },
  {
    "id": "安全管理部门",
    "name": "安全管理部门",
    "entityType": "岗位角色",
    "degree": 101
  },
  {
    "id": "高处作业",
    "name": "高处作业",
    "entityType": "作业类型",
    "degree": 91
  },
  {
    "id": "动火作业",
    "name": "动火作业",
    "entityType": "作业类型",
    "degree": 84
  },
  {
    "id": "安全教育培训",
    "name": "安全教育培训",
    "entityType": "管理职责",
    "degree": 70
  },
  {
    "id": "触电事故",
    "name": "触电事故",
    "entityType": "风险因素",
    "degree": 68
  },
  {
    "id": "高处坠落",
    "name": "高处坠落",
    "entityType": "风险因素",
    "degree": 68
  },
  {
    "id": "吊装作业",
    "name": "吊装作业",
    "entityType": "作业类型",
    "degree": 63
  },
  {
    "id": "生产安全事故隐患排查治理制度",
    "name": "生产安全事故隐患排查治理制度",
    "entityType": "法规标准",
    "degree": 49
  },
  {
    "id": "应急管理制度",
    "name": "应急管理制度",
    "entityType": "法规标准",
    "degree": 39
  },
  {
    "id": "机械伤害事故",
    "name": "机械伤害事故",
    "entityType": "风险因素",
    "degree": 37
  },
  {
    "id": "临时用电作业",
    "name": "临时用电作业",
    "entityType": "作业类型",
    "degree": 37
  },
  {
    "id": "中毒窒息",
    "name": "中毒窒息",
    "entityType": "风险因素",
    "degree": 35
  },
  {
    "id": "临时用电作业安全操作规程",
    "name": "临时用电作业安全操作规程",
    "entityType": "法规标准",
    "degree": 34
  },
  {
    "id": "坠落",
    "name": "坠落",
    "entityType": "风险因素",
    "degree": 34
  },
  {
    "id": "事故",
    "name": "事故",
    "entityType": "风险因素",
    "degree": 32
  },
  {
    "id": "防坠落用品",
    "name": "防坠落用品",
    "entityType": "防护用品",
    "degree": 31
  },
  {
    "id": "应急器材",
    "name": "应急器材",
    "entityType": "安全措施",
    "degree": 30
  },
  {
    "id": "企业主要负责人",
    "name": "企业主要负责人",
    "entityType": "岗位角色",
    "degree": 30
  },
  {
    "id": "坠落死亡",
    "name": "坠落死亡",
    "entityType": "风险因素",
    "degree": 29
  },
  {
    "id": "承包商（相关方）安全管理制度",
    "name": "承包商（相关方）安全管理制度",
    "entityType": "法规标准",
    "degree": 29
  },
  {
    "id": "应急预案",
    "name": "应急预案",
    "entityType": "安全措施",
    "degree": 29
  },
  {
    "id": "属地单位",
    "name": "属地单位",
    "entityType": "岗位角色",
    "degree": 28
  },
  {
    "id": "承包商人员",
    "name": "承包商人员",
    "entityType": "岗位角色",
    "degree": 26
  },
  {
    "id": "安全生产责任制",
    "name": "安全生产责任制",
    "entityType": "管理职责",
    "degree": 26
  },
  {
    "id": "中华人民共和国安全生产法",
    "name": "中华人民共和国安全生产法",
    "entityType": "法规标准",
    "degree": 26
  },
  {
    "id": "应急领导小组",
    "name": "应急领导小组",
    "entityType": "管理职责",
    "degree": 25
  },
  {
    "id": "监护人",
    "name": "监护人",
    "entityType": "岗位角色",
    "degree": 24
  },
  {
    "id": "检维修作业",
    "name": "检维修作业",
    "entityType": "作业类型",
    "degree": 24
  },
  {
    "id": "发包部门",
    "name": "发包部门",
    "entityType": "岗位角色",
    "degree": 23
  },
  {
    "id": "起重吊装作业安全操作规程",
    "name": "起重吊装作业安全操作规程",
    "entityType": "法规标准",
    "degree": 22
  },
  {
    "id": "清淤作业",
    "name": "清淤作业",
    "entityType": "作业类型",
    "degree": 21
  },
  {
    "id": "技术与其他保障",
    "name": "技术与其他保障",
    "entityType": "管理职责",
    "degree": 21
  },
  {
    "id": "监护",
    "name": "监护",
    "entityType": "安全措施",
    "degree": 21
  },
  {
    "id": "电气检修",
    "name": "电气检修",
    "entityType": "作业类型",
    "degree": 21
  },
  {
    "id": "各部门、车间",
    "name": "各部门、车间",
    "entityType": "管理职责",
    "degree": 18
  },
  {
    "id": "车间主任",
    "name": "车间主任",
    "entityType": "岗位角色",
    "degree": 18
  },
  {
    "id": "公司",
    "name": "公司",
    "entityType": "管理职责",
    "degree": 18
  },
  {
    "id": "预案修订",
    "name": "预案修订",
    "entityType": "安全措施",
    "degree": 18
  },
  {
    "id": "中毒死亡",
    "name": "中毒死亡",
    "entityType": "风险因素",
    "degree": 17
  },
  {
    "id": "现场人员",
    "name": "现场人员",
    "entityType": "岗位角色",
    "degree": 17
  },
  {
    "id": "本规程",
    "name": "本规程",
    "entityType": "法规标准",
    "degree": 17
  },
  {
    "id": "受限空间作业安全操作规程",
    "name": "受限空间作业安全操作规程",
    "entityType": "法规标准",
    "degree": 17
  },
  {
    "id": "特种登高作业人员",
    "name": "特种登高作业人员",
    "entityType": "岗位角色",
    "degree": 17
  },
  {
    "id": "培训考核结果",
    "name": "培训考核结果",
    "entityType": "管理职责",
    "degree": 17
  },
  {
    "id": "主要负责人",
    "name": "主要负责人",
    "entityType": "岗位角色",
    "degree": 17
  },
  {
    "id": "动火安全作业证",
    "name": "动火安全作业证",
    "entityType": "法规标准",
    "degree": 17
  },
  {
    "id": "承包商",
    "name": "承包商",
    "entityType": "岗位角色",
    "degree": 16
  },
  {
    "id": "班组长",
    "name": "班组长",
    "entityType": "岗位角色",
    "degree": 16
  },
  {
    "id": "安全工器具管理",
    "name": "安全工器具管理",
    "entityType": "安全措施",
    "degree": 16
  },
  {
    "id": "电气火灾",
    "name": "电气火灾",
    "entityType": "风险因素",
    "degree": 16
  },
  {
    "id": "表彰奖励",
    "name": "表彰奖励",
    "entityType": "管理职责",
    "degree": 16
  },
  {
    "id": "处罚",
    "name": "处罚",
    "entityType": "管理职责",
    "degree": 16
  },
  {
    "id": "正压式空气呼吸器",
    "name": "正压式空气呼吸器",
    "entityType": "防护用品",
    "degree": 16
  },
  {
    "id": "电气设备着火",
    "name": "电气设备着火",
    "entityType": "风险因素",
    "degree": 15
  },
  {
    "id": "安全培训档案",
    "name": "安全培训档案",
    "entityType": "管理职责",
    "degree": 15
  },
  {
    "id": "佐证材料",
    "name": "佐证材料",
    "entityType": "管理职责",
    "degree": 15
  },
  {
    "id": "特种作业",
    "name": "特种作业",
    "entityType": "作业类型",
    "degree": 15
  },
  {
    "id": "应急演练",
    "name": "应急演练",
    "entityType": "安全措施",
    "degree": 14
  },
  {
    "id": "特殊作业",
    "name": "特殊作业",
    "entityType": "作业类型",
    "degree": 14
  },
  {
    "id": "作业证",
    "name": "作业证",
    "entityType": "安全措施",
    "degree": 14
  },
  {
    "id": "隐患排查",
    "name": "隐患排查",
    "entityType": "安全措施",
    "degree": 14
  },
  {
    "id": "验收",
    "name": "验收",
    "entityType": "安全措施",
    "degree": 14
  },
  {
    "id": "隐患排查台账",
    "name": "隐患排查台账",
    "entityType": "管理职责",
    "degree": 13
  },
  {
    "id": "高处作业防护",
    "name": "高处作业防护",
    "entityType": "安全措施",
    "degree": 13
  },
  {
    "id": "安全生产委员会",
    "name": "安全生产委员会",
    "entityType": "管理职责",
    "degree": 13
  },
  {
    "id": "从业人员",
    "name": "从业人员",
    "entityType": "岗位角色",
    "degree": 13
  },
  {
    "id": "隐患分类与排查内容",
    "name": "隐患分类与排查内容",
    "entityType": "管理职责",
    "degree": 13
  },
  {
    "id": "作业结束收尾",
    "name": "作业结束收尾",
    "entityType": "作业环节",
    "degree": 13
  },
  {
    "id": "立即中止作业",
    "name": "立即中止作业",
    "entityType": "管理职责",
    "degree": 13
  },
  {
    "id": "有限空间",
    "name": "有限空间",
    "entityType": "作业环节",
    "degree": 13
  },
  {
    "id": "漏电保护器缺失或失效",
    "name": "漏电保护器缺失或失效",
    "entityType": "风险因素",
    "degree": 13
  },
  {
    "id": "安全交底",
    "name": "安全交底",
    "entityType": "管理职责",
    "degree": 13
  },
  {
    "id": "高处作业安全操作规程",
    "name": "高处作业安全操作规程",
    "entityType": "法规标准",
    "degree": 12
  },
  {
    "id": "使用验电器验电",
    "name": "使用验电器验电",
    "entityType": "安全措施",
    "degree": 12
  },
  {
    "id": "预案编制",
    "name": "预案编制",
    "entityType": "作业环节",
    "degree": 12
  },
  {
    "id": "违章作业",
    "name": "违章作业",
    "entityType": "风险因素",
    "degree": 12
  },
  {
    "id": "安委会办公室",
    "name": "安委会办公室",
    "entityType": "管理职责",
    "degree": 12
  },
  {
    "id": "隐患排查治理信息台账",
    "name": "隐患排查治理信息台账",
    "entityType": "安全措施",
    "degree": 12
  },
  {
    "id": "压力机",
    "name": "压力机",
    "entityType": "设备设施",
    "degree": 12
  },
  {
    "id": "电工",
    "name": "电工",
    "entityType": "岗位角色",
    "degree": 12
  },
  {
    "id": "事故隐患",
    "name": "事故隐患",
    "entityType": "风险因素",
    "degree": 12
  },
  {
    "id": "演练评估结果",
    "name": "演练评估结果",
    "entityType": "管理职责",
    "degree": 12
  },
  {
    "id": "应急处置",
    "name": "应急处置",
    "entityType": "安全措施",
    "degree": 12
  },
  {
    "id": "触电死亡",
    "name": "触电死亡",
    "entityType": "风险因素",
    "degree": 11
  },
  {
    "id": "燃爆",
    "name": "燃爆",
    "entityType": "风险因素",
    "degree": 11
  },
  {
    "id": "临时用电设施",
    "name": "临时用电设施",
    "entityType": "设备设施",
    "degree": 11
  },
  {
    "id": "安全网",
    "name": "安全网",
    "entityType": "安全措施",
    "degree": 11
  },
  {
    "id": "安全管理人员",
    "name": "安全管理人员",
    "entityType": "岗位角色",
    "degree": 10
  },
  {
    "id": "企业",
    "name": "企业",
    "entityType": "管理职责",
    "degree": 10
  },
  {
    "id": "生产安全事故",
    "name": "生产安全事故",
    "entityType": "风险因素",
    "degree": 10
  },
  {
    "id": "吊物坠落",
    "name": "吊物坠落",
    "entityType": "风险因素",
    "degree": 10
  },
  {
    "id": "液氨泄漏",
    "name": "液氨泄漏",
    "entityType": "风险因素",
    "degree": 10
  },
  {
    "id": "高处安全作业证",
    "name": "高处安全作业证",
    "entityType": "法规标准",
    "degree": 10
  },
  {
    "id": "气体检测仪检测",
    "name": "气体检测仪检测",
    "entityType": "安全措施",
    "degree": 10
  },
  {
    "id": "评估报告",
    "name": "评估报告",
    "entityType": "安全措施",
    "degree": 10
  },
  {
    "id": "作业组",
    "name": "作业组",
    "entityType": "岗位角色",
    "degree": 10
  },
  {
    "id": "动火作业安全操作规程",
    "name": "动火作业安全操作规程",
    "entityType": "法规标准",
    "degree": 10
  },
  {
    "id": "劳动防护用品使用",
    "name": "劳动防护用品使用",
    "entityType": "安全措施",
    "degree": 10
  },
  {
    "id": "电工作业",
    "name": "电工作业",
    "entityType": "作业类型",
    "degree": 10
  },
  {
    "id": "入场安全教育",
    "name": "入场安全教育",
    "entityType": "安全措施",
    "degree": 10
  },
  {
    "id": "安全绳",
    "name": "安全绳",
    "entityType": "防护用品",
    "degree": 9
  },
  {
    "id": "恢复送电",
    "name": "恢复送电",
    "entityType": "作业环节",
    "degree": 9
  },
  {
    "id": "配电柜",
    "name": "配电柜",
    "entityType": "设备设施",
    "degree": 9
  },
  {
    "id": "专项检查",
    "name": "专项检查",
    "entityType": "管理职责",
    "degree": 9
  },
  {
    "id": "伤亡扩大",
    "name": "伤亡扩大",
    "entityType": "风险因素",
    "degree": 9
  },
  {
    "id": "有限空间中毒窒息事故",
    "name": "有限空间中毒窒息事故",
    "entityType": "风险因素",
    "degree": 9
  },
  {
    "id": "较大生产安全责任事故",
    "name": "较大生产安全责任事故",
    "entityType": "风险因素",
    "degree": 9
  },
  {
    "id": "气体检测仪",
    "name": "气体检测仪",
    "entityType": "设备设施",
    "degree": 9
  },
  {
    "id": "分管安全生产负责人",
    "name": "分管安全生产负责人",
    "entityType": "岗位角色",
    "degree": 9
  },
  {
    "id": "重大隐患治理",
    "name": "重大隐患治理",
    "entityType": "管理职责",
    "degree": 9
  },
  {
    "id": "心肺复苏",
    "name": "心肺复苏",
    "entityType": "安全措施",
    "degree": 9
  },
  {
    "id": "排查治理失效",
    "name": "排查治理失效",
    "entityType": "风险因素",
    "degree": 9
  },
  {
    "id": "验电器",
    "name": "验电器",
    "entityType": "防护用品",
    "degree": 9
  },
  {
    "id": "起重机械司机",
    "name": "起重机械司机",
    "entityType": "岗位角色",
    "degree": 9
  },
  {
    "id": "隐患整改",
    "name": "隐患整改",
    "entityType": "安全措施",
    "degree": 9
  },
  {
    "id": "月度安全绩效考核",
    "name": "月度安全绩效考核",
    "entityType": "管理职责",
    "degree": 9
  },
  {
    "id": "教育培训",
    "name": "教育培训",
    "entityType": "安全措施",
    "degree": 9
  },
  {
    "id": "物体打击",
    "name": "物体打击",
    "entityType": "风险因素",
    "degree": 9
  },
  {
    "id": "员工",
    "name": "员工",
    "entityType": "岗位角色",
    "degree": 9
  },
  {
    "id": "作业前准备",
    "name": "作业前准备",
    "entityType": "作业环节",
    "degree": 9
  },
  {
    "id": "头部防护用品",
    "name": "头部防护用品",
    "entityType": "防护用品",
    "degree": 9
  },
  {
    "id": "安全绩效评价",
    "name": "安全绩效评价",
    "entityType": "管理职责",
    "degree": 9
  },
  {
    "id": "培训记录弄虚作假",
    "name": "培训记录弄虚作假",
    "entityType": "风险因素",
    "degree": 9
  },
  {
    "id": "日常排查",
    "name": "日常排查",
    "entityType": "管理职责",
    "degree": 9
  },
  {
    "id": "报告事故信息",
    "name": "报告事故信息",
    "entityType": "作业环节",
    "degree": 9
  },
  {
    "id": "周某",
    "name": "周某",
    "entityType": "岗位角色",
    "degree": 9
  },
  {
    "id": "组织培训效果评估",
    "name": "组织培训效果评估",
    "entityType": "管理职责",
    "degree": 8
  },
  {
    "id": "三脚架",
    "name": "三脚架",
    "entityType": "设备设施",
    "degree": 8
  },
  {
    "id": "手持式电动工具",
    "name": "手持式电动工具",
    "entityType": "设备设施",
    "degree": 8
  },
  {
    "id": "未佩戴任何呼吸防护器材",
    "name": "未佩戴任何呼吸防护器材",
    "entityType": "防护用品",
    "degree": 8
  },
  {
    "id": "整改措施",
    "name": "整改措施",
    "entityType": "安全措施",
    "degree": 8
  },
  {
    "id": "全过程闭环管理",
    "name": "全过程闭环管理",
    "entityType": "管理职责",
    "degree": 8
  },
  {
    "id": "绝缘鞋",
    "name": "绝缘鞋",
    "entityType": "防护用品",
    "degree": 8
  },
  {
    "id": "承包商作业人员",
    "name": "承包商作业人员",
    "entityType": "岗位角色",
    "degree": 8
  },
  {
    "id": "可燃有毒气体检测报警系统",
    "name": "可燃有毒气体检测报警系统",
    "entityType": "设备设施",
    "degree": 8
  },
  {
    "id": "停电挂牌",
    "name": "停电挂牌",
    "entityType": "安全措施",
    "degree": 8
  },
  {
    "id": "作业人员",
    "name": "作业人员",
    "entityType": "岗位角色",
    "degree": 8
  },
  {
    "id": "作业许可证",
    "name": "作业许可证",
    "entityType": "作业环节",
    "degree": 8
  },
  {
    "id": "电气设备停电检修",
    "name": "电气设备停电检修",
    "entityType": "作业类型",
    "degree": 8
  },
  {
    "id": "现场处置方案",
    "name": "现场处置方案",
    "entityType": "法规标准",
    "degree": 8
  },
  {
    "id": "安全协议签订",
    "name": "安全协议签订",
    "entityType": "管理职责",
    "degree": 8
  },
  {
    "id": "持证上岗",
    "name": "持证上岗",
    "entityType": "管理职责",
    "degree": 8
  },
  {
    "id": "指挥人员",
    "name": "指挥人员",
    "entityType": "岗位角色",
    "degree": 8
  },
  {
    "id": "通风",
    "name": "通风",
    "entityType": "安全措施",
    "degree": 8
  },
  {
    "id": "置换处理",
    "name": "置换处理",
    "entityType": "安全措施",
    "degree": 8
  },
  {
    "id": "高风险作业",
    "name": "高风险作业",
    "entityType": "作业类型",
    "degree": 8
  },
  {
    "id": "重大危险源管理",
    "name": "重大危险源管理",
    "entityType": "管理职责",
    "degree": 8
  },
  {
    "id": "死亡",
    "name": "死亡",
    "entityType": "风险因素",
    "degree": 8
  },
  {
    "id": "可燃气体",
    "name": "可燃气体",
    "entityType": "化学物质",
    "degree": 8
  }
],
  links: [
  {
    "source": "液氨泄漏",
    "target": "中毒死亡",
    "relation": "导致",
    "confidence": 0.9
  },
  {
    "source": "正压式空气呼吸器",
    "target": "应急器材",
    "relation": "配套",
    "confidence": 0.88
  },
  {
    "source": "正压式空气呼吸器",
    "target": "有限空间作业",
    "relation": "适用于",
    "confidence": 0.9
  },
  {
    "source": "正压式空气呼吸器",
    "target": "中毒窒息",
    "relation": "防止",
    "confidence": 0.9
  },
  {
    "source": "正压式空气呼吸器",
    "target": "中毒死亡",
    "relation": "防止",
    "confidence": 0.95
  },
  {
    "source": "企业",
    "target": "中华人民共和国安全生产法",
    "relation": "依据",
    "confidence": 0.9
  },
  {
    "source": "企业",
    "target": "事故",
    "relation": "责任于",
    "confidence": 0.9
  },
  {
    "source": "可燃有毒气体检测报警系统",
    "target": "立即中止作业",
    "relation": "防止",
    "confidence": 0.9
  },
  {
    "source": "安全管理部门",
    "target": "事故隐患",
    "relation": "通报",
    "confidence": 0.85
  },
  {
    "source": "安全管理部门",
    "target": "事故隐患",
    "relation": "汇总",
    "confidence": 0.85
  },
  {
    "source": "安全管理部门",
    "target": "安全教育培训",
    "relation": "责任于",
    "confidence": 0.9
  },
  {
    "source": "安全管理部门",
    "target": "组织培训效果评估",
    "relation": "责任于",
    "confidence": 0.92
  },
  {
    "source": "安全管理部门",
    "target": "隐患排查",
    "relation": "责任于",
    "confidence": 0.95
  },
  {
    "source": "安全管理部门",
    "target": "应急预案",
    "relation": "责任于",
    "confidence": 0.9
  },
  {
    "source": "安全管理部门",
    "target": "应急演练",
    "relation": "责任于",
    "confidence": 0.9
  },
  {
    "source": "安全管理部门",
    "target": "劳动防护用品使用",
    "relation": "责任于",
    "confidence": 0.9
  },
  {
    "source": "安全管理部门",
    "target": "违章作业",
    "relation": "禁止",
    "confidence": 0.88
  },
  {
    "source": "安全管理部门",
    "target": "安全绩效评价",
    "relation": "责任于",
    "confidence": 0.9
  },
  {
    "source": "未佩戴任何呼吸防护器材",
    "target": "伤亡扩大",
    "relation": "导致",
    "confidence": 0.85
  },
  {
    "source": "企业主要负责人",
    "target": "承包商（相关方）安全管理制度",
    "relation": "责任于",
    "confidence": 0.9
  },
  {
    "source": "企业主要负责人",
    "target": "重大危险源管理",
    "relation": "责任于",
    "confidence": 0.85
  },
  {
    "source": "事故",
    "target": "发包部门",
    "relation": "责任于",
    "confidence": 0.85
  },
  {
    "source": "检维修作业",
    "target": "中华人民共和国安全生产法",
    "relation": "依据",
    "confidence": 0.95
  },
  {
    "source": "检维修作业",
    "target": "使用验电器验电",
    "relation": "前置条件",
    "confidence": 0.9
  },
  {
    "source": "检维修作业",
    "target": "触电事故",
    "relation": "导致",
    "confidence": 0.9
  },
  {
    "source": "现场处置方案",
    "target": "应急处置",
    "relation": "包含",
    "confidence": 0.9
  },
  {
    "source": "动火作业",
    "target": "作业许可证",
    "relation": "前置条件",
    "confidence": 0.85
  },
  {
    "source": "动火作业",
    "target": "作业许可证",
    "relation": "配套",
    "confidence": 0.85
  },
  {
    "source": "动火作业",
    "target": "监护人",
    "relation": "前置条件",
    "confidence": 0.95
  },
  {
    "source": "动火作业",
    "target": "安全交底",
    "relation": "配套",
    "confidence": 0.9
  },
  {
    "source": "动火作业",
    "target": "气体检测仪",
    "relation": "配套",
    "confidence": 0.9
  },
  {
    "source": "动火作业",
    "target": "特种作业",
    "relation": "属于",
    "confidence": 0.9
  },
  {
    "source": "动火作业",
    "target": "防坠落用品",
    "relation": "配套",
    "confidence": 0.95
  },
  {
    "source": "动火作业",
    "target": "特殊作业",
    "relation": "属于",
    "confidence": 0.9
  },
  {
    "source": "动火作业",
    "target": "高处坠落",
    "relation": "导致",
    "confidence": 0.9
  },
  {
    "source": "动火作业",
    "target": "动火作业安全操作规程",
    "relation": "依据",
    "confidence": 0.9
  },
  {
    "source": "动火作业",
    "target": "动火安全作业证",
    "relation": "依据",
    "confidence": 0.95
  },
  {
    "source": "动火作业",
    "target": "气体检测仪检测",
    "relation": "配套",
    "confidence": 0.9
  },
  {
    "source": "动火作业",
    "target": "安全交底",
    "relation": "前置条件",
    "confidence": 0.92
  },
  {
    "source": "动火作业",
    "target": "动火安全作业证",
    "relation": "前置条件",
    "confidence": 0.9
  },
  {
    "source": "动火作业",
    "target": "监护",
    "relation": "前置条件",
    "confidence": 0.9
  },
  {
    "source": "动火作业",
    "target": "有限空间作业",
    "relation": "包含",
    "confidence": 0.8
  },
  {
    "source": "动火作业",
    "target": "高处作业",
    "relation": "包含",
    "confidence": 0.8
  },
  {
    "source": "动火作业",
    "target": "吊装作业",
    "relation": "包含",
    "confidence": 0.8
  },
  {
    "source": "主要负责人",
    "target": "重大隐患治理",
    "relation": "责任于",
    "confidence": 0.85
  },
  {
    "source": "主要负责人",
    "target": "安全教育培训",
    "relation": "责任于",
    "confidence": 0.85
  },
  {
    "source": "主要负责人",
    "target": "安全教育培训",
    "relation": "依据",
    "confidence": 0.9
  },
  {
    "source": "演练评估结果",
    "target": "评估报告",
    "relation": "包含",
    "confidence": 0.9
  },
  {
    "source": "有限空间",
    "target": "中毒窒息",
    "relation": "导致",
    "confidence": 0.85
  },
  {
    "source": "中毒窒息",
    "target": "正压式空气呼吸器",
    "relation": "防止",
    "confidence": 0.9
  },
  {
    "source": "清淤作业",
    "target": "监护人",
    "relation": "配套",
    "confidence": 0.88
  },
  {
    "source": "清淤作业",
    "target": "有限空间作业",
    "relation": "包含",
    "confidence": 0.85
  },
  {
    "source": "清淤作业",
    "target": "通风",
    "relation": "前置条件",
    "confidence": 0.9
  },
  {
    "source": "清淤作业",
    "target": "监护",
    "relation": "配套",
    "confidence": 0.75
  },
  {
    "source": "清淤作业",
    "target": "有限空间作业",
    "relation": "属于",
    "confidence": 0.9
  },
  {
    "source": "清淤作业",
    "target": "中毒窒息",
    "relation": "导致",
    "confidence": 0.9
  },
  {
    "source": "有限空间作业",
    "target": "作业结束收尾",
    "relation": "包含",
    "confidence": 0.92
  },
  {
    "source": "有限空间作业",
    "target": "气体检测仪",
    "relation": "配套",
    "confidence": 0.95
  },
  {
    "source": "有限空间作业",
    "target": "受限空间作业安全操作规程",
    "relation": "适用于",
    "confidence": 0.9
  },
  {
    "source": "有限空间作业",
    "target": "特种作业",
    "relation": "属于",
    "confidence": 0.9
  },
  {
    "source": "有限空间作业",
    "target": "防坠落用品",
    "relation": "配套",
    "confidence": 0.9
  },
  {
    "source": "有限空间作业",
    "target": "违章作业",
    "relation": "禁止",
    "confidence": 0.8
  },
  {
    "source": "有限空间作业",
    "target": "应急预案",
    "relation": "依据",
    "confidence": 0.9
  },
  {
    "source": "有限空间作业",
    "target": "置换处理",
    "relation": "前置条件",
    "confidence": 0.9
  },
  {
    "source": "有限空间作业",
    "target": "正压式空气呼吸器",
    "relation": "配套",
    "confidence": 0.9
  },
  {
    "source": "有限空间作业",
    "target": "安全绳",
    "relation": "配套",
    "confidence": 0.9
  },
  {
    "source": "有限空间作业",
    "target": "三脚架",
    "relation": "配套",
    "confidence": 0.9
  },
  {
    "source": "有限空间作业",
    "target": "头部防护用品",
    "relation": "配套",
    "confidence": 0.95
  },
  {
    "source": "有限空间作业",
    "target": "漏电保护器缺失或失效",
    "relation": "配套",
    "confidence": 0.9
  },
  {
    "source": "有限空间作业",
    "target": "安全交底",
    "relation": "前置条件",
    "confidence": 0.92
  },
  {
    "source": "有限空间作业",
    "target": "气体检测仪检测",
    "relation": "配套",
    "confidence": 0.95
  },
  {
    "source": "有限空间作业",
    "target": "置换处理",
    "relation": "配套",
    "confidence": 0.9
  },
  {
    "source": "有限空间作业",
    "target": "通风",
    "relation": "配套",
    "confidence": 0.9
  },
  {
    "source": "有限空间作业",
    "target": "监护",
    "relation": "配套",
    "confidence": 0.9
  },
  {
    "source": "有限空间作业",
    "target": "清淤作业",
    "relation": "包含",
    "confidence": 0.85
  },
  {
    "source": "有限空间作业",
    "target": "通风",
    "relation": "前置条件",
    "confidence": 0.9
  },
  {
    "source": "有限空间作业",
    "target": "中华人民共和国安全生产法",
    "relation": "依据",
    "confidence": 0.95
  },
  {
    "source": "有限空间作业",
    "target": "应急器材",
    "relation": "配套",
    "confidence": 0.85
  },
  {
    "source": "有限空间作业",
    "target": "中毒窒息",
    "relation": "导致",
    "confidence": 0.95
  },
  {
    "source": "有限空间作业",
    "target": "特殊作业",
    "relation": "属于",
    "confidence": 0.9
  },
  {
    "source": "有限空间作业",
    "target": "中毒死亡",
    "relation": "导致",
    "confidence": 0.9
  },
  {
    "source": "有限空间作业",
    "target": "燃爆",
    "relation": "导致",
    "confidence": 0.9
  },
  {
    "source": "作业组",
    "target": "气体检测仪检测",
    "relation": "禁止",
    "confidence": 0.8
  },
  {
    "source": "作业组",
    "target": "通风",
    "relation": "禁止",
    "confidence": 0.8
  },
  {
    "source": "通风",
    "target": "有限空间作业",
    "relation": "适用于",
    "confidence": 0.75
  },
  {
    "source": "气体检测仪检测",
    "target": "可燃气体",
    "relation": "包含",
    "confidence": 0.9
  },
  {
    "source": "气体检测仪检测",
    "target": "中毒窒息",
    "relation": "防止",
    "confidence": 0.85
  },
  {
    "source": "周某",
    "target": "安全交底",
    "relation": "责任于",
    "confidence": 0.9
  },
  {
    "source": "周某",
    "target": "中毒窒息",
    "relation": "导致",
    "confidence": 0.9
  },
  {
    "source": "周某",
    "target": "未佩戴任何呼吸防护器材",
    "relation": "禁止",
    "confidence": 0.85
  },
  {
    "source": "周某",
    "target": "高处坠落",
    "relation": "责任于",
    "confidence": 0.9
  },
  {
    "source": "周某",
    "target": "作业组",
    "relation": "属于",
    "confidence": 0.9
  },
  {
    "source": "监护",
    "target": "立即中止作业",
    "relation": "责任于",
    "confidence": 0.9
  },
  {
    "source": "监护",
    "target": "动火作业",
    "relation": "责任于",
    "confidence": 0.92
  },
  {
    "source": "作业人员",
    "target": "安全教育培训",
    "relation": "责任于",
    "confidence": 0.9
  },
  {
    "source": "作业人员",
    "target": "持证上岗",
    "relation": "责任于",
    "confidence": 0.85
  },
  {
    "source": "作业人员",
    "target": "持证上岗",
    "relation": "配套",
    "confidence": 0.9
  },
  {
    "source": "作业人员",
    "target": "应急演练",
    "relation": "责任于",
    "confidence": 0.75
  },
  {
    "source": "应急演练",
    "target": "评估报告",
    "relation": "配套",
    "confidence": 0.88
  },
  {
    "source": "应急演练",
    "target": "演练评估结果",
    "relation": "前置条件",
    "confidence": 0.88
  },
  {
    "source": "应急器材",
    "target": "气体检测仪",
    "relation": "包含",
    "confidence": 0.95
  },
  {
    "source": "应急器材",
    "target": "气体检测仪检测",
    "relation": "包含",
    "confidence": 0.95
  },
  {
    "source": "应急器材",
    "target": "防坠落用品",
    "relation": "包含",
    "confidence": 0.9
  },
  {
    "source": "应急器材",
    "target": "安全绳",
    "relation": "包含",
    "confidence": 0.9
  },
  {
    "source": "应急器材",
    "target": "三脚架",
    "relation": "包含",
    "confidence": 0.9
  },
  {
    "source": "应急器材",
    "target": "正压式空气呼吸器",
    "relation": "包含",
    "confidence": 0.95
  },
  {
    "source": "三脚架",
    "target": "坠落",
    "relation": "防止",
    "confidence": 0.7
  },
  {
    "source": "三脚架",
    "target": "有限空间作业",
    "relation": "适用于",
    "confidence": 0.9
  },
  {
    "source": "安全绳",
    "target": "中毒死亡",
    "relation": "防止",
    "confidence": 0.7
  },
  {
    "source": "安全绳",
    "target": "坠落",
    "relation": "防止",
    "confidence": 0.85
  },
  {
    "source": "安全绳",
    "target": "高处作业",
    "relation": "适用于",
    "confidence": 0.9
  },
  {
    "source": "安全绳",
    "target": "有限空间作业",
    "relation": "适用于",
    "confidence": 0.9
  },
  {
    "source": "防坠落用品",
    "target": "坠落",
    "relation": "防止",
    "confidence": 0.9
  },
  {
    "source": "防坠落用品",
    "target": "高处作业",
    "relation": "配套",
    "confidence": 0.95
  },
  {
    "source": "防坠落用品",
    "target": "高处作业",
    "relation": "适用于",
    "confidence": 0.9
  },
  {
    "source": "防坠落用品",
    "target": "坠落死亡",
    "relation": "防止",
    "confidence": 0.9
  },
  {
    "source": "防坠落用品",
    "target": "高处坠落",
    "relation": "防止",
    "confidence": 0.9
  },
  {
    "source": "隐患排查",
    "target": "月度安全绩效考核",
    "relation": "依据",
    "confidence": 0.9
  },
  {
    "source": "隐患排查",
    "target": "机械伤害事故",
    "relation": "防止",
    "confidence": 0.85
  },
  {
    "source": "员工",
    "target": "事故隐患",
    "relation": "报告",
    "confidence": 0.85
  },
  {
    "source": "教育培训",
    "target": "有限空间作业",
    "relation": "前置条件",
    "confidence": 0.9
  },
  {
    "source": "教育培训",
    "target": "高处坠落",
    "relation": "防止",
    "confidence": 0.75
  },
  {
    "source": "压力机",
    "target": "机械伤害事故",
    "relation": "导致",
    "confidence": 0.85
  },
  {
    "source": "车间主任",
    "target": "隐患整改",
    "relation": "责任于",
    "confidence": 0.9
  },
  {
    "source": "安全教育培训",
    "target": "安全管理部门",
    "relation": "责任于",
    "confidence": 0.92
  },
  {
    "source": "安全教育培训",
    "target": "高处坠落",
    "relation": "防止",
    "confidence": 0.9
  },
  {
    "source": "安全教育培训",
    "target": "机械伤害事故",
    "relation": "防止",
    "confidence": 0.85
  },
  {
    "source": "安全教育培训",
    "target": "高处坠落",
    "relation": "导致",
    "confidence": 0.85
  },
  {
    "source": "安全教育培训",
    "target": "中华人民共和国安全生产法",
    "relation": "依据",
    "confidence": 0.95
  },
  {
    "source": "安全教育培训",
    "target": "承包商作业人员",
    "relation": "适用于",
    "confidence": 0.92
  },
  {
    "source": "安全教育培训",
    "target": "劳动防护用品使用",
    "relation": "包含",
    "confidence": 0.9
  },
  {
    "source": "安全教育培训",
    "target": "高处作业",
    "relation": "前置条件",
    "confidence": 0.9
  },
  {
    "source": "电工",
    "target": "本规程",
    "relation": "依据",
    "confidence": 0.9
  },
  {
    "source": "电工",
    "target": "触电事故",
    "relation": "责任于",
    "confidence": 0.85
  },
  {
    "source": "电工",
    "target": "持证上岗",
    "relation": "依据",
    "confidence": 0.88
  },
  {
    "source": "电工",
    "target": "特种登高作业人员",
    "relation": "属于",
    "confidence": 0.95
  },
  {
    "source": "电工",
    "target": "检维修作业",
    "relation": "责任于",
    "confidence": 0.85
  },
  {
    "source": "心肺复苏",
    "target": "触电死亡",
    "relation": "防止",
    "confidence": 0.85
  },
  {
    "source": "心肺复苏",
    "target": "触电事故",
    "relation": "防止",
    "confidence": 0.85
  },
  {
    "source": "心肺复苏",
    "target": "死亡",
    "relation": "防止",
    "confidence": 0.8
  },
  {
    "source": "安全工器具管理",
    "target": "使用验电器验电",
    "relation": "包含",
    "confidence": 0.9
  },
  {
    "source": "安全工器具管理",
    "target": "绝缘鞋",
    "relation": "包含",
    "confidence": 0.9
  },
  {
    "source": "安全工器具管理",
    "target": "验电器",
    "relation": "包含",
    "confidence": 0.95
  },
  {
    "source": "验电器",
    "target": "触电事故",
    "relation": "防止",
    "confidence": 0.9
  },
  {
    "source": "验电器",
    "target": "安全工器具管理",
    "relation": "属于",
    "confidence": 0.9
  },
  {
    "source": "电气检修",
    "target": "使用验电器验电",
    "relation": "配套",
    "confidence": 0.9
  },
  {
    "source": "电气检修",
    "target": "使用验电器验电",
    "relation": "包含",
    "confidence": 0.9
  },
  {
    "source": "电气检修",
    "target": "停电挂牌",
    "relation": "包含",
    "confidence": 0.9
  },
  {
    "source": "电气检修",
    "target": "验电器",
    "relation": "配套",
    "confidence": 0.9
  },
  {
    "source": "电气检修",
    "target": "停电挂牌",
    "relation": "配套",
    "confidence": 0.9
  },
  {
    "source": "停电挂牌",
    "target": "触电死亡",
    "relation": "防止",
    "confidence": 0.75
  },
  {
    "source": "绝缘鞋",
    "target": "安全工器具管理",
    "relation": "属于",
    "confidence": 0.9
  },
  {
    "source": "电工作业",
    "target": "使用验电器验电",
    "relation": "配套",
    "confidence": 0.9
  },
  {
    "source": "电工作业",
    "target": "使用验电器验电",
    "relation": "包含",
    "confidence": 0.95
  },
  {
    "source": "电工作业",
    "target": "验电器",
    "relation": "配套",
    "confidence": 0.9
  },
  {
    "source": "电工作业",
    "target": "绝缘鞋",
    "relation": "配套",
    "confidence": 0.95
  },
  {
    "source": "电工作业",
    "target": "验电器",
    "relation": "包含",
    "confidence": 0.95
  },
  {
    "source": "电工作业",
    "target": "停电挂牌",
    "relation": "包含",
    "confidence": 0.95
  },
  {
    "source": "高处坠落",
    "target": "事故",
    "relation": "属于",
    "confidence": 0.85
  },
  {
    "source": "高处坠落",
    "target": "死亡",
    "relation": "导致",
    "confidence": 0.95
  },
  {
    "source": "高处坠落",
    "target": "事故",
    "relation": "导致",
    "confidence": 0.85
  },
  {
    "source": "入场安全教育",
    "target": "应急处置",
    "relation": "包含",
    "confidence": 0.85
  },
  {
    "source": "入场安全教育",
    "target": "高处坠落",
    "relation": "防止",
    "confidence": 0.88
  },
  {
    "source": "高处作业",
    "target": "高处作业安全操作规程",
    "relation": "依据",
    "confidence": 0.9
  },
  {
    "source": "高处作业",
    "target": "坠落",
    "relation": "导致",
    "confidence": 0.9
  },
  {
    "source": "高处作业",
    "target": "特种作业",
    "relation": "属于",
    "confidence": 0.9
  },
  {
    "source": "高处作业",
    "target": "安全网",
    "relation": "配套",
    "confidence": 0.9
  },
  {
    "source": "高处作业",
    "target": "中华人民共和国安全生产法",
    "relation": "依据",
    "confidence": 0.95
  },
  {
    "source": "高处作业",
    "target": "绝缘鞋",
    "relation": "配套",
    "confidence": 0.9
  },
  {
    "source": "高处作业",
    "target": "高处坠落",
    "relation": "导致",
    "confidence": 0.92
  },
  {
    "source": "高处作业",
    "target": "防坠落用品",
    "relation": "配套",
    "confidence": 0.95
  },
  {
    "source": "高处作业",
    "target": "头部防护用品",
    "relation": "配套",
    "confidence": 0.95
  },
  {
    "source": "高处作业",
    "target": "特种登高作业人员",
    "relation": "属于",
    "confidence": 0.9
  },
  {
    "source": "高处作业",
    "target": "特殊作业",
    "relation": "属于",
    "confidence": 0.9
  },
  {
    "source": "高处作业",
    "target": "高处作业防护",
    "relation": "依据",
    "confidence": 0.85
  },
  {
    "source": "高处作业",
    "target": "物体打击",
    "relation": "导致",
    "confidence": 0.9
  },
  {
    "source": "高处作业",
    "target": "坠落死亡",
    "relation": "导致",
    "confidence": 0.9
  },
  {
    "source": "高处作业",
    "target": "高处安全作业证",
    "relation": "依据",
    "confidence": 0.95
  },
  {
    "source": "高处作业",
    "target": "安全网",
    "relation": "前置条件",
    "confidence": 0.92
  },
  {
    "source": "高处作业",
    "target": "高处作业",
    "relation": "包含",
    "confidence": 0.9
  },
  {
    "source": "高处作业",
    "target": "高处作业",
    "relation": "属于",
    "confidence": 0.8
  },
  {
    "source": "安全交底",
    "target": "高处坠落",
    "relation": "防止",
    "confidence": 0.85
  },
  {
    "source": "安全网",
    "target": "高处坠落",
    "relation": "防止",
    "confidence": 0.9
  },
  {
    "source": "头部防护用品",
    "target": "高处作业",
    "relation": "适用于",
    "confidence": 0.9
  },
  {
    "source": "公司",
    "target": "隐患排查台账",
    "relation": "包含",
    "confidence": 0.9
  },
  {
    "source": "公司",
    "target": "隐患排查治理信息台账",
    "relation": "建立",
    "confidence": 0.85
  },
  {
    "source": "公司",
    "target": "应急演练",
    "relation": "责任于",
    "confidence": 0.85
  },
  {
    "source": "隐患整改",
    "target": "高处坠落",
    "relation": "防止",
    "confidence": 0.85
  },
  {
    "source": "特种登高作业人员",
    "target": "持证上岗",
    "relation": "前置条件",
    "confidence": 0.9
  },
  {
    "source": "特种登高作业人员",
    "target": "持证上岗",
    "relation": "责任于",
    "confidence": 0.9
  },
  {
    "source": "安全培训档案",
    "target": "评估报告",
    "relation": "包含",
    "confidence": 0.85
  },
  {
    "source": "安全培训档案",
    "target": "安全管理部门",
    "relation": "责任于",
    "confidence": 0.9
  },
  {
    "source": "高处作业防护",
    "target": "安全管理部门",
    "relation": "责任于",
    "confidence": 0.95
  },
  {
    "source": "高处作业防护",
    "target": "应急处置",
    "relation": "包含",
    "confidence": 0.9
  },
  {
    "source": "高处作业防护",
    "target": "高处作业",
    "relation": "适用于",
    "confidence": 0.95
  },
  {
    "source": "高处作业防护",
    "target": "中华人民共和国安全生产法",
    "relation": "依据",
    "confidence": 0.95
  },
  {
    "source": "承包商作业人员",
    "target": "入场安全教育",
    "relation": "前置条件",
    "confidence": 0.9
  },
  {
    "source": "承包商作业人员",
    "target": "入场安全教育",
    "relation": "责任于",
    "confidence": 0.93
  },
  {
    "source": "安全管理人员",
    "target": "安全教育培训",
    "relation": "责任于",
    "confidence": 0.85
  },
  {
    "source": "安全管理人员",
    "target": "安全教育培训",
    "relation": "依据",
    "confidence": 0.9
  },
  {
    "source": "各部门、车间",
    "target": "安全教育培训",
    "relation": "依据",
    "confidence": 0.85
  },
  {
    "source": "各部门、车间",
    "target": "生产安全事故隐患排查治理制度",
    "relation": "依据",
    "confidence": 0.9
  },
  {
    "source": "各部门、车间",
    "target": "验收",
    "relation": "责任于",
    "confidence": 0.85
  },
  {
    "source": "安全生产责任制",
    "target": "中华人民共和国安全生产法",
    "relation": "依据",
    "confidence": 0.95
  },
  {
    "source": "安全生产委员会",
    "target": "分管安全生产负责人",
    "relation": "责任于",
    "confidence": 0.95
  },
  {
    "source": "安全生产委员会",
    "target": "企业主要负责人",
    "relation": "责任于",
    "confidence": 0.95
  },
  {
    "source": "安委会办公室",
    "target": "安全管理部门",
    "relation": "责任于",
    "confidence": 0.9
  },
  {
    "source": "安委会办公室",
    "target": "安全生产委员会",
    "relation": "属于",
    "confidence": 0.95
  },
  {
    "source": "安委会办公室",
    "target": "安全管理部门",
    "relation": "属于",
    "confidence": 0.9
  },
  {
    "source": "应急预案",
    "target": "应急管理制度",
    "relation": "依据",
    "confidence": 0.85
  },
  {
    "source": "应急预案",
    "target": "预案修订",
    "relation": "包含",
    "confidence": 0.85
  },
  {
    "source": "应急预案",
    "target": "中毒窒息",
    "relation": "适用于",
    "confidence": 0.9
  },
  {
    "source": "应急预案",
    "target": "高处坠落",
    "relation": "适用于",
    "confidence": 0.9
  },
  {
    "source": "应急预案",
    "target": "机械伤害事故",
    "relation": "适用于",
    "confidence": 0.9
  },
  {
    "source": "应急预案",
    "target": "触电事故",
    "relation": "适用于",
    "confidence": 0.9
  },
  {
    "source": "从业人员",
    "target": "应急演练",
    "relation": "责任于",
    "confidence": 0.95
  },
  {
    "source": "从业人员",
    "target": "安全教育培训",
    "relation": "责任于",
    "confidence": 0.95
  },
  {
    "source": "从业人员",
    "target": "劳动防护用品使用",
    "relation": "责任于",
    "confidence": 0.95
  },
  {
    "source": "处罚",
    "target": "安全生产责任制",
    "relation": "依据",
    "confidence": 0.8
  },
  {
    "source": "违章作业",
    "target": "生产安全事故",
    "relation": "导致",
    "confidence": 0.9
  },
  {
    "source": "违章作业",
    "target": "事故",
    "relation": "导致",
    "confidence": 0.95
  },
  {
    "source": "违章作业",
    "target": "处罚",
    "relation": "导致",
    "confidence": 0.85
  },
  {
    "source": "应急管理制度",
    "target": "应急处置",
    "relation": "包含",
    "confidence": 0.85
  },
  {
    "source": "应急管理制度",
    "target": "技术与其他保障",
    "relation": "包含",
    "confidence": 0.9
  },
  {
    "source": "应急管理制度",
    "target": "应急演练",
    "relation": "包含",
    "confidence": 0.85
  },
  {
    "source": "应急管理制度",
    "target": "应急处置",
    "relation": "适用于",
    "confidence": 0.95
  },
  {
    "source": "应急管理制度",
    "target": "应急器材",
    "relation": "适用于",
    "confidence": 0.9
  },
  {
    "source": "应急管理制度",
    "target": "中华人民共和国安全生产法",
    "relation": "依据",
    "confidence": 0.95
  },
  {
    "source": "应急领导小组",
    "target": "主要负责人",
    "relation": "责任于",
    "confidence": 0.92
  },
  {
    "source": "应急领导小组",
    "target": "主要负责人",
    "relation": "包含",
    "confidence": 0.95
  },
  {
    "source": "预案修订",
    "target": "应急处置",
    "relation": "包含",
    "confidence": 0.85
  },
  {
    "source": "承包商（相关方）安全管理制度",
    "target": "安全管理部门",
    "relation": "责任于",
    "confidence": 0.92
  },
  {
    "source": "承包商（相关方）安全管理制度",
    "target": "教育培训",
    "relation": "包含",
    "confidence": 0.9
  },
  {
    "source": "承包商（相关方）安全管理制度",
    "target": "生产安全事故",
    "relation": "防止",
    "confidence": 0.8
  },
  {
    "source": "承包商（相关方）安全管理制度",
    "target": "中华人民共和国安全生产法",
    "relation": "依据",
    "confidence": 0.95
  },
  {
    "source": "发包部门",
    "target": "生产安全事故",
    "relation": "责任于",
    "confidence": 0.75
  },
  {
    "source": "发包部门",
    "target": "事故",
    "relation": "责任于",
    "confidence": 0.85
  },
  {
    "source": "发包部门",
    "target": "安全绩效评价",
    "relation": "责任于",
    "confidence": 0.9
  },
  {
    "source": "发包部门",
    "target": "验收",
    "relation": "责任于",
    "confidence": 0.9
  },
  {
    "source": "发包部门",
    "target": "安全协议签订",
    "relation": "责任于",
    "confidence": 0.95
  },
  {
    "source": "属地单位",
    "target": "生产安全事故",
    "relation": "责任于",
    "confidence": 0.75
  },
  {
    "source": "属地单位",
    "target": "安全交底",
    "relation": "责任于",
    "confidence": 0.9
  },
  {
    "source": "属地单位",
    "target": "验收",
    "relation": "责任于",
    "confidence": 0.9
  },
  {
    "source": "属地单位",
    "target": "立即中止作业",
    "relation": "责任于",
    "confidence": 0.9
  },
  {
    "source": "属地单位",
    "target": "承包商作业人员",
    "relation": "责任于",
    "confidence": 0.85
  },
  {
    "source": "全过程闭环管理",
    "target": "作业许可证",
    "relation": "包含",
    "confidence": 0.88
  },
  {
    "source": "承包商",
    "target": "事故",
    "relation": "责任于",
    "confidence": 0.9
  },
  {
    "source": "承包商",
    "target": "生产安全事故",
    "relation": "责任于",
    "confidence": 0.9
  },
  {
    "source": "承包商",
    "target": "应急器材",
    "relation": "配套",
    "confidence": 0.8
  },
  {
    "source": "承包商",
    "target": "劳动防护用品使用",
    "relation": "配套",
    "confidence": 0.8
  },
  {
    "source": "承包商",
    "target": "安全生产责任制",
    "relation": "依据",
    "confidence": 0.82
  },
  {
    "source": "特殊作业",
    "target": "临时用电作业",
    "relation": "包含",
    "confidence": 0.95
  },
  {
    "source": "特殊作业",
    "target": "吊装作业",
    "relation": "包含",
    "confidence": 0.95
  },
  {
    "source": "特殊作业",
    "target": "高处作业",
    "relation": "包含",
    "confidence": 0.95
  },
  {
    "source": "特殊作业",
    "target": "有限空间作业",
    "relation": "包含",
    "confidence": 0.95
  },
  {
    "source": "特殊作业",
    "target": "动火作业",
    "relation": "包含",
    "confidence": 0.95
  },
  {
    "source": "特殊作业",
    "target": "作业许可证",
    "relation": "前置条件",
    "confidence": 0.9
  },
  {
    "source": "吊装作业",
    "target": "特殊作业",
    "relation": "属于",
    "confidence": 0.9
  },
  {
    "source": "吊装作业",
    "target": "物体打击",
    "relation": "导致",
    "confidence": 0.9
  },
  {
    "source": "吊装作业",
    "target": "起重吊装作业安全操作规程",
    "relation": "依据",
    "confidence": 0.85
  },
  {
    "source": "吊装作业",
    "target": "中华人民共和国安全生产法",
    "relation": "依据",
    "confidence": 0.95
  },
  {
    "source": "吊装作业",
    "target": "监护",
    "relation": "配套",
    "confidence": 0.85
  },
  {
    "source": "吊装作业",
    "target": "特种作业",
    "relation": "属于",
    "confidence": 0.9
  },
  {
    "source": "吊装作业",
    "target": "作业许可证",
    "relation": "前置条件",
    "confidence": 0.85
  },
  {
    "source": "吊装作业",
    "target": "吊装作业",
    "relation": "禁止",
    "confidence": 0.85
  },
  {
    "source": "临时用电作业",
    "target": "作业许可证",
    "relation": "前置条件",
    "confidence": 0.85
  },
  {
    "source": "临时用电作业",
    "target": "中华人民共和国安全生产法",
    "relation": "依据",
    "confidence": 0.95
  },
  {
    "source": "临时用电作业",
    "target": "临时用电作业安全操作规程",
    "relation": "属于",
    "confidence": 0.8
  },
  {
    "source": "临时用电作业",
    "target": "电气火灾",
    "relation": "防止",
    "confidence": 0.92
  },
  {
    "source": "临时用电作业",
    "target": "触电事故",
    "relation": "防止",
    "confidence": 0.92
  },
  {
    "source": "临时用电作业",
    "target": "特种作业",
    "relation": "属于",
    "confidence": 0.9
  },
  {
    "source": "临时用电作业",
    "target": "验收",
    "relation": "前置条件",
    "confidence": 0.85
  },
  {
    "source": "临时用电作业",
    "target": "电工",
    "relation": "责任于",
    "confidence": 0.9
  },
  {
    "source": "临时用电作业",
    "target": "临时用电作业安全操作规程",
    "relation": "依据",
    "confidence": 0.85
  },
  {
    "source": "临时用电作业",
    "target": "电气火灾",
    "relation": "导致",
    "confidence": 0.9
  },
  {
    "source": "临时用电作业",
    "target": "触电事故",
    "relation": "导致",
    "confidence": 0.9
  },
  {
    "source": "临时用电作业",
    "target": "特殊作业",
    "relation": "属于",
    "confidence": 0.9
  },
  {
    "source": "安全绩效评价",
    "target": "事故",
    "relation": "包含",
    "confidence": 0.85
  },
  {
    "source": "事故隐患",
    "target": "主要负责人",
    "relation": "责任于",
    "confidence": 0.85
  },
  {
    "source": "事故隐患",
    "target": "事故",
    "relation": "导致",
    "confidence": 0.85
  },
  {
    "source": "事故隐患",
    "target": "事故隐患",
    "relation": "属于",
    "confidence": 0.95
  },
  {
    "source": "事故隐患",
    "target": "生产安全事故隐患排查治理制度",
    "relation": "属于",
    "confidence": 0.85
  },
  {
    "source": "佐证材料",
    "target": "安全协议签订",
    "relation": "包含",
    "confidence": 0.85
  },
  {
    "source": "生产安全事故隐患排查治理制度",
    "target": "监护人",
    "relation": "包含",
    "confidence": 0.85
  },
  {
    "source": "生产安全事故隐患排查治理制度",
    "target": "安全管理部门",
    "relation": "责任于",
    "confidence": 0.85
  },
  {
    "source": "生产安全事故隐患排查治理制度",
    "target": "监护",
    "relation": "包含",
    "confidence": 0.9
  },
  {
    "source": "生产安全事故隐患排查治理制度",
    "target": "应急器材",
    "relation": "包含",
    "confidence": 0.85
  },
  {
    "source": "生产安全事故隐患排查治理制度",
    "target": "持证上岗",
    "relation": "包含",
    "confidence": 0.85
  },
  {
    "source": "生产安全事故隐患排查治理制度",
    "target": "安全生产责任制",
    "relation": "包含",
    "confidence": 0.85
  },
  {
    "source": "生产安全事故隐患排查治理制度",
    "target": "隐患分类与排查内容",
    "relation": "包含",
    "confidence": 0.9
  },
  {
    "source": "生产安全事故隐患排查治理制度",
    "target": "中华人民共和国安全生产法",
    "relation": "依据",
    "confidence": 0.95
  },
  {
    "source": "生产安全事故隐患排查治理制度",
    "target": "生产安全事故",
    "relation": "防止",
    "confidence": 0.9
  },
  {
    "source": "重大隐患治理",
    "target": "生产安全事故隐患排查治理制度",
    "relation": "依据",
    "confidence": 0.9
  },
  {
    "source": "重大隐患治理",
    "target": "验收",
    "relation": "包含",
    "confidence": 0.9
  },
  {
    "source": "隐患排查治理信息台账",
    "target": "验收",
    "relation": "包含",
    "confidence": 0.85
  },
  {
    "source": "隐患排查治理信息台账",
    "target": "整改措施",
    "relation": "包含",
    "confidence": 0.9
  },
  {
    "source": "临时用电作业安全操作规程",
    "target": "作业前准备",
    "relation": "包含",
    "confidence": 0.9
  },
  {
    "source": "临时用电作业安全操作规程",
    "target": "安全管理部门",
    "relation": "责任于",
    "confidence": 0.92
  },
  {
    "source": "临时用电作业安全操作规程",
    "target": "应急处置",
    "relation": "包含",
    "confidence": 0.85
  },
  {
    "source": "临时用电作业安全操作规程",
    "target": "手持式电动工具",
    "relation": "包含",
    "confidence": 0.9
  },
  {
    "source": "临时用电作业安全操作规程",
    "target": "检维修作业",
    "relation": "包含",
    "confidence": 0.9
  },
  {
    "source": "临时用电作业安全操作规程",
    "target": "临时用电设施",
    "relation": "适用于",
    "confidence": 0.95
  },
  {
    "source": "临时用电作业安全操作规程",
    "target": "临时用电作业",
    "relation": "适用于",
    "confidence": 0.95
  },
  {
    "source": "临时用电作业安全操作规程",
    "target": "中华人民共和国安全生产法",
    "relation": "依据",
    "confidence": 0.95
  },
  {
    "source": "漏电保护器缺失或失效",
    "target": "触电事故",
    "relation": "导致",
    "confidence": 0.85
  },
  {
    "source": "漏电保护器缺失或失效",
    "target": "触电事故",
    "relation": "防止",
    "confidence": 0.85
  },
  {
    "source": "电气设备停电检修",
    "target": "使用验电器验电",
    "relation": "配套",
    "confidence": 0.9
  },
  {
    "source": "电气设备停电检修",
    "target": "验电器",
    "relation": "配套",
    "confidence": 0.9
  },
  {
    "source": "电气设备停电检修",
    "target": "停电挂牌",
    "relation": "配套",
    "confidence": 0.9
  },
  {
    "source": "动火作业安全操作规程",
    "target": "应急处置",
    "relation": "包含",
    "confidence": 0.85
  },
  {
    "source": "动火作业安全操作规程",
    "target": "作业前准备",
    "relation": "包含",
    "confidence": 0.85
  },
  {
    "source": "动火作业安全操作规程",
    "target": "动火作业",
    "relation": "适用于",
    "confidence": 0.95
  },
  {
    "source": "动火作业安全操作规程",
    "target": "中华人民共和国安全生产法",
    "relation": "依据",
    "confidence": 0.9
  },
  {
    "source": "可燃气体",
    "target": "燃爆",
    "relation": "导致",
    "confidence": 0.95
  },
  {
    "source": "作业前准备",
    "target": "可燃有毒气体检测报警系统",
    "relation": "包含",
    "confidence": 0.85
  },
  {
    "source": "动火安全作业证",
    "target": "安全管理部门",
    "relation": "属于",
    "confidence": 0.7
  },
  {
    "source": "动火安全作业证",
    "target": "监护人",
    "relation": "包含",
    "confidence": 0.85
  },
  {
    "source": "动火安全作业证",
    "target": "车间主任",
    "relation": "责任于",
    "confidence": 0.9
  },
  {
    "source": "动火安全作业证",
    "target": "安全管理部门",
    "relation": "责任于",
    "confidence": 0.9
  },
  {
    "source": "作业证",
    "target": "安全管理部门",
    "relation": "责任于",
    "confidence": 0.85
  },
  {
    "source": "作业证",
    "target": "有限空间作业",
    "relation": "属于",
    "confidence": 0.85
  },
  {
    "source": "作业证",
    "target": "监护",
    "relation": "包含",
    "confidence": 0.8
  },
  {
    "source": "置换处理",
    "target": "通风",
    "relation": "配套",
    "confidence": 0.9
  },
  {
    "source": "本规程",
    "target": "物体打击",
    "relation": "防止",
    "confidence": 0.85
  },
  {
    "source": "本规程",
    "target": "中华人民共和国安全生产法",
    "relation": "依据",
    "confidence": 0.95
  },
  {
    "source": "本规程",
    "target": "安全管理部门",
    "relation": "责任于",
    "confidence": 0.95
  },
  {
    "source": "受限空间作业安全操作规程",
    "target": "安全管理部门",
    "relation": "责任于",
    "confidence": 0.95
  },
  {
    "source": "受限空间作业安全操作规程",
    "target": "应急处置",
    "relation": "包含",
    "confidence": 0.9
  },
  {
    "source": "受限空间作业安全操作规程",
    "target": "作业前准备",
    "relation": "包含",
    "confidence": 0.85
  },
  {
    "source": "受限空间作业安全操作规程",
    "target": "有限空间作业",
    "relation": "适用于",
    "confidence": 0.95
  },
  {
    "source": "受限空间作业安全操作规程",
    "target": "燃爆",
    "relation": "防止",
    "confidence": 0.85
  },
  {
    "source": "受限空间作业安全操作规程",
    "target": "中毒死亡",
    "relation": "防止",
    "confidence": 0.85
  },
  {
    "source": "受限空间作业安全操作规程",
    "target": "中华人民共和国安全生产法",
    "relation": "依据",
    "confidence": 0.85
  },
  {
    "source": "起重吊装作业安全操作规程",
    "target": "安全管理部门",
    "relation": "责任于",
    "confidence": 0.95
  },
  {
    "source": "起重吊装作业安全操作规程",
    "target": "应急处置",
    "relation": "包含",
    "confidence": 0.85
  },
  {
    "source": "起重吊装作业安全操作规程",
    "target": "作业前准备",
    "relation": "包含",
    "confidence": 0.85
  },
  {
    "source": "起重吊装作业安全操作规程",
    "target": "吊装作业",
    "relation": "适用于",
    "confidence": 0.9
  },
  {
    "source": "起重吊装作业安全操作规程",
    "target": "中华人民共和国安全生产法",
    "relation": "依据",
    "confidence": 0.9
  },
  {
    "source": "起重机械司机",
    "target": "作业人员",
    "relation": "属于",
    "confidence": 0.9
  },
  {
    "source": "起重机械司机",
    "target": "头部防护用品",
    "relation": "配套",
    "confidence": 0.95
  },
  {
    "source": "指挥人员",
    "target": "作业人员",
    "relation": "属于",
    "confidence": 0.9
  },
  {
    "source": "指挥人员",
    "target": "头部防护用品",
    "relation": "配套",
    "confidence": 0.95
  },
  {
    "source": "吊物坠落",
    "target": "立即中止作业",
    "relation": "导致",
    "confidence": 0.85
  },
  {
    "source": "高处安全作业证",
    "target": "作业人员",
    "relation": "包含",
    "confidence": 0.8
  },
  {
    "source": "高处安全作业证",
    "target": "安全管理部门",
    "relation": "责任于",
    "confidence": 0.85
  },
  {
    "source": "高处安全作业证",
    "target": "车间主任",
    "relation": "责任于",
    "confidence": 0.85
  },
  {
    "source": "气体检测仪",
    "target": "可燃气体",
    "relation": "包含",
    "confidence": 0.9
  },
  {
    "source": "气体检测仪",
    "target": "中毒窒息",
    "relation": "防止",
    "confidence": 0.9
  },
  {
    "source": "监护人",
    "target": "立即中止作业",
    "relation": "责任于",
    "confidence": 0.9
  },
  {
    "source": "监护人",
    "target": "有限空间作业",
    "relation": "适用于",
    "confidence": 0.75
  },
  {
    "source": "使用验电器验电",
    "target": "安全工器具管理",
    "relation": "属于",
    "confidence": 0.9
  },
  {
    "source": "使用验电器验电",
    "target": "触电死亡",
    "relation": "防止",
    "confidence": 0.75
  },
  {
    "source": "使用验电器验电",
    "target": "触电事故",
    "relation": "防止",
    "confidence": 0.85
  },
  {
    "source": "高处作业安全操作规程",
    "target": "安全管理部门",
    "relation": "责任于",
    "confidence": 0.92
  },
  {
    "source": "高处作业安全操作规程",
    "target": "应急处置",
    "relation": "包含",
    "confidence": 0.85
  },
  {
    "source": "高处作业安全操作规程",
    "target": "作业前准备",
    "relation": "包含",
    "confidence": 0.9
  },
  {
    "source": "高处作业安全操作规程",
    "target": "高处作业安全操作规程",
    "relation": "依据",
    "confidence": 0.95
  },
  {
    "source": "高处作业安全操作规程",
    "target": "中华人民共和国安全生产法",
    "relation": "依据",
    "confidence": 0.95
  },
  {
    "source": "高处作业安全操作规程",
    "target": "高处作业",
    "relation": "适用于",
    "confidence": 0.95
  },
  {
    "source": "隐患排查台账",
    "target": "整改措施",
    "relation": "包含",
    "confidence": 0.9
  },
  {
    "source": "特种作业",
    "target": "临时用电作业",
    "relation": "包含",
    "confidence": 0.9
  },
  {
    "source": "特种作业",
    "target": "吊装作业",
    "relation": "包含",
    "confidence": 0.9
  },
  {
    "source": "特种作业",
    "target": "高处作业",
    "relation": "包含",
    "confidence": 0.9
  },
  {
    "source": "特种作业",
    "target": "有限空间作业",
    "relation": "包含",
    "confidence": 0.9
  },
  {
    "source": "特种作业",
    "target": "动火作业",
    "relation": "包含",
    "confidence": 0.9
  },
  {
    "source": "特种作业",
    "target": "作业许可证",
    "relation": "依据",
    "confidence": 0.9
  },
  {
    "source": "承包商人员",
    "target": "违章作业",
    "relation": "责任于",
    "confidence": 0.8
  },
  {
    "source": "承包商人员",
    "target": "生产安全事故",
    "relation": "责任于",
    "confidence": 0.85
  },
  {
    "source": "承包商人员",
    "target": "监护人",
    "relation": "配套",
    "confidence": 0.85
  },
  {
    "source": "承包商人员",
    "target": "较大生产安全责任事故",
    "relation": "禁止",
    "confidence": 0.8
  },
  {
    "source": "承包商人员",
    "target": "应急器材",
    "relation": "配套",
    "confidence": 0.85
  },
  {
    "source": "承包商人员",
    "target": "劳动防护用品使用",
    "relation": "配套",
    "confidence": 0.85
  },
  {
    "source": "承包商人员",
    "target": "安全管理人员",
    "relation": "配套",
    "confidence": 0.8
  },
  {
    "source": "承包商人员",
    "target": "安全生产责任制",
    "relation": "配套",
    "confidence": 0.85
  },
  {
    "source": "承包商人员",
    "target": "承包商（相关方）安全管理制度",
    "relation": "依据",
    "confidence": 0.95
  },
  {
    "source": "承包商人员",
    "target": "入场安全教育",
    "relation": "前置条件",
    "confidence": 0.9
  }
],
}

/** 后端 /overview 返回的全图统计 */
export const REAL_GRAPH_STATS = {
  entities: 2840,
  relations: 3850,
  communities: 223,
}
