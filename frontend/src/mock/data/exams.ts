import type { ExamResult, ExamSummary, Position, Question } from '@/types'

export const EXAM_LIST: ExamSummary[] = [
  {
    id: 'exam-001',
    title: '井控安全专项考核',
    position: '司钻',
    tags: ['井控', '防喷', '溢流处置'],
    questionCount: 6,
    difficulty: 3,
    durationMin: 20,
    status: 'pending',
    totalScore: 100,
    deadline: '2026-10-20',
  },
  {
    id: 'exam-002',
    title: '硫化氢防护月度测验',
    position: '司钻',
    tags: ['硫化氢', '应急响应'],
    questionCount: 6,
    difficulty: 2,
    durationMin: 15,
    status: 'pending',
    totalScore: 100,
    deadline: '2026-10-18',
  },
  {
    id: 'exam-003',
    title: '个人防护装备规范测验',
    position: '钻工',
    tags: ['PPE', '高处作业'],
    questionCount: 5,
    difficulty: 1,
    durationMin: 10,
    status: 'pending',
    totalScore: 100,
    deadline: '2026-10-25',
  },
  {
    id: 'exam-004',
    title: '10 月井控综合考核',
    position: '司钻',
    tags: ['井控', '关井程序'],
    questionCount: 6,
    difficulty: 4,
    durationMin: 25,
    status: 'finished',
    totalScore: 100,
    gotScore: 86,
    deadline: '2026-10-05',
  },
]

const QUESTIONS_001: Question[] = [
  {
    id: 'q1',
    type: 'single',
    stem: '发现溢流后应立即执行的第一步动作是？',
    options: ['发出长鸣警报', '直接压井', '撤离井场', '加大泵速循环观察'],
    answer: 'A',
    score: 15,
    knowledgeTags: ['溢流处置'],
    difficulty: 2,
  },
  {
    id: 'q2',
    type: 'single',
    stem: '软关井程序中，关闭防喷器闸板前应先完成哪一步？',
    options: ['打开液动平板阀', '关节流阀', '停泵并上提钻具', '记录立压套压'],
    answer: 'C',
    score: 15,
    knowledgeTags: ['关井程序'],
    difficulty: 3,
  },
  {
    id: 'q3',
    type: 'multiple',
    stem: '关井后需要持续监测的参数有哪些？（多选）',
    options: ['立管压力', '套管压力', '钻井液池体积增量', '天气温度'],
    answer: 'ABC',
    score: 20,
    knowledgeTags: ['关井程序', '井控监测'],
    difficulty: 3,
  },
  {
    id: 'q4',
    type: 'judge',
    stem: '硬关井是指先关节流阀再关防喷器的关井方式。',
    options: [],
    answer: '错',
    score: 10,
    knowledgeTags: ['关井程序'],
    difficulty: 2,
  },
  {
    id: 'q5',
    type: 'judge',
    stem: '溢流发生后，若及时按程序关井，可以有效防止井喷失控。',
    options: [],
    answer: '对',
    score: 10,
    knowledgeTags: ['井控'],
    difficulty: 1,
  },
  {
    id: 'q6',
    type: 'short_answer',
    stem: '简述软关井的基本步骤及其优点。',
    options: [],
    answer:
      '步骤：①发警报；②停泵上提钻具；③开液动平板阀关防喷器闸板；④关节流阀试关井；⑤观察压力并汇报。优点：先关环空后关节流阀，井口承受冲击小，可观察套压变化便于后续压井决策。',
    score: 30,
    knowledgeTags: ['关井程序'],
    difficulty: 4,
  },
]

const QUESTIONS_002: Question[] = [
  {
    id: 'q1',
    type: 'single',
    stem: '硫化氢浓度达到多少 ppm 时必须佩戴正压式空气呼吸器？',
    options: ['5 ppm', '10 ppm', '20 ppm', '100 ppm'],
    answer: 'C',
    score: 25,
    knowledgeTags: ['硫化氢', '分级响应'],
    difficulty: 2,
  },
  {
    id: 'q2',
    type: 'single',
    stem: '发现硫化氢中毒人员，第一步应做什么？',
    options: ['立即人工呼吸', '转移至上风向通风处', '喂水', '等待医生'],
    answer: 'B',
    score: 25,
    knowledgeTags: ['急救'],
    difficulty: 1,
  },
  {
    id: 'q3',
    type: 'judge',
    stem: '硫化氢比空气轻，容易在井口上方聚集。',
    options: [],
    answer: '错',
    score: 20,
    knowledgeTags: ['硫化氢'],
    difficulty: 2,
  },
  {
    id: 'q4',
    type: 'judge',
    stem: '硫化氢监测报警后，非必要人员应向上风向撤离。',
    options: [],
    answer: '对',
    score: 20,
    knowledgeTags: ['应急响应'],
    difficulty: 1,
  },
  {
    id: 'q5',
    type: 'short_answer',
    stem: '简述硫化氢三级浓度报警值及对应响应措施。',
    options: [],
    answer:
      '10ppm 一级预警：检查泄漏点；20ppm 二级预警：佩戴正压式空气呼吸器作业；100ppm 危险浓度：立即撤离并上报应急指挥。',
    score: 10,
    knowledgeTags: ['分级响应'],
    difficulty: 3,
  },
]

const QUESTIONS_003: Question[] = [
  {
    id: 'q1',
    type: 'single',
    stem: '进入井场作业区必须佩戴的安全帽要求是？',
    options: ['反戴透气', '下颏带收紧', '帽内垫报纸', '颜色随意'],
    answer: 'B',
    score: 30,
    knowledgeTags: ['PPE'],
    difficulty: 1,
  },
  {
    id: 'q2',
    type: 'judge',
    stem: '高处作业使用安全带应遵循"高挂低用"原则。',
    options: [],
    answer: '对',
    score: 30,
    knowledgeTags: ['高处作业'],
    difficulty: 1,
  },
  {
    id: 'q3',
    type: 'short_answer',
    stem: '列举井场入场"三件套"个人防护装备。',
    options: [],
    answer: '安全帽（下颏带收紧）、防砸防穿刺劳保鞋、反光背心（含护目镜）。',
    score: 40,
    knowledgeTags: ['PPE'],
    difficulty: 1,
  },
]

export const PAPERS: Record<string, Question[]> = {
  'exam-001': QUESTIONS_001,
  'exam-002': QUESTIONS_002,
  'exam-003': QUESTIONS_003,
}

export const EXAM_RESULTS: Record<string, ExamResult> = {
  'exam-004': {
    exam: EXAM_LIST[3],
    gotScore: 86,
    objectiveCorrectRate: 0.8,
    weakTags: ['井控监测', '压井作业'],
    rubric: [
      { dimension: '准确性', score: 9, full: 10 },
      { dimension: '完整性', score: 8, full: 10 },
      { dimension: '条理性', score: 9, full: 10 },
      { dimension: '规范性', score: 8.5, full: 10 },
    ],
    questions: QUESTIONS_001.map((q) => {
      if (q.type === 'short_answer') {
        return {
          ...q,
          grading: {
            userAnswer:
              '先发警报，然后停泵上提钻具，关防喷器和节流阀，最后观察压力汇报。',
            gotScore: 26,
            rubricScores: { 准确性: 9, 完整性: 8, 条理性: 9, 规范性: 8.5 },
            reason:
              '步骤基本正确，但缺少「开液动平板阀」与「试关井」两个关键动作（-3），优点表述完整（扣分依据规程 5.3 节）。',
            references: [
              '钻井井控技术规程 第 5.3 节：软关井程序应包含发警报、停泵上提、关防喷器、关节流阀试关井、观察汇报五个环节。',
              '井控设备操作手册 第 4 章：液动平板阀应在关闸板前打开，避免憋压。',
            ],
          },
        }
      }
      return q
    }).map((q, i) =>
      i === 2
        ? { ...q, answer: 'ABC', grading: { userAnswer: 'AB', gotScore: 0, rubricScores: {}, reason: '漏选 C：钻井液池增量是判断溢流的核心参数。', references: [] } }
        : q,
    ),
  },
}

export function positionOfExam(id: string): Position {
  return EXAM_LIST.find((e) => e.id === id)?.position ?? '司钻'
}

let genSeq = 0

/**
 * AI 出卷发布：把生成的试卷注册为正式考试。
 * EXAM_LIST / PAPERS 为模块级 mock 数据，发布后工人端考试中心立即可见、可作答、可批改。
 */
export function registerGeneratedExam(
  paper: Question[],
  meta: { position: Position; tags: string[]; difficulty: 1 | 2 | 3 | 4 | 5 },
): ExamSummary {
  genSeq += 1
  const id = `exam-gen-${genSeq}`
  const exam: ExamSummary = {
    id,
    title: `AI 生成卷 · ${meta.tags.join('/')}`,
    position: meta.position,
    tags: meta.tags,
    questionCount: paper.length,
    difficulty: meta.difficulty,
    durationMin: Math.max(10, paper.length * 4),
    status: 'pending',
    totalScore: paper.reduce((s, q) => s + q.score, 0),
    deadline: new Date(Date.now() + 7 * 86_400_000).toISOString().slice(0, 10),
  }
  EXAM_LIST.unshift(exam)
  PAPERS[id] = paper
  return exam
}
