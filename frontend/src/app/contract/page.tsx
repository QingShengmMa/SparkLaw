'use client';

import { useState, useRef, useEffect } from 'react';
import { Upload, FileText, AlertTriangle, CheckCircle, Loader2, AlertCircle, ExternalLink } from 'lucide-react';
import ScaleIcon from '@/components/ScaleIcon';
import { uploadDocument, reviewContract, getReviewTaskStatus, ContractReviewResponse, RiskLevel, ReviewTaskStatusResponse } from '@/lib/api';

// 思考链终端组件
function ThinkingTerminal({ steps, isActive }: { steps: string[]; isActive: boolean }) {
  const terminalRef = useRef<HTMLDivElement>(null);

  return (
    <div className="card overflow-hidden">
      <div className="flex items-center justify-between border-b border-border bg-muted px-4 py-2">
        <div className="flex items-center gap-2">
          <div className="flex gap-1.5">
            <div className="h-3 w-3 rounded-full bg-red-500"></div>
            <div className="h-3 w-3 rounded-full bg-yellow-500"></div>
            <div className="h-3 w-3 rounded-full bg-green-500"></div>
          </div>
          <span className="text-sm text-muted-foreground ml-2">SparkLaw AI Agent Terminal</span>
        </div>
        {isActive && (
          <div className="flex items-center gap-2 text-xs text-green-500">
            <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse-subtle"></div>
            Processing...
          </div>
        )}
      </div>
      
      <div 
        ref={terminalRef}
        className="h-64 overflow-y-auto p-4 font-mono text-sm space-y-1"
      >
        {steps.length === 0 && (
          <div className="text-muted-foreground italic">等待处理...</div>
        )}
        {steps.map((step, index) => (
          <div key={index} className="leading-relaxed animate-fadeIn">
            {step}
          </div>
        ))}
        {isActive && (
          <div className="flex items-center gap-2 text-primary">
            <Loader2 size={14} className="animate-spin" />
            <span className="animate-pulse">思考中...</span>
          </div>
        )}
      </div>
    </div>
  );
}

export default function ContractPage() {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [reviewing, setReviewing] = useState(false);
  const [contractId, setContractId] = useState<string>('');
  const [uploadResult, setUploadResult] = useState<any>(null);
  const [reviewResult, setReviewResult] = useState<ContractReviewResponse | null>(null);
  const [reviewTaskId, setReviewTaskId] = useState<string>('');
  const [reviewProgress, setReviewProgress] = useState<number>(0);
  const [reviewStatusMessage, setReviewStatusMessage] = useState<string>('');
  const [error, setError] = useState<string>('');
  const [thinkingSteps, setThinkingSteps] = useState<string[]>([]);
  const [isDragging, setIsDragging] = useState(false);

  useEffect(() => {
    if (!reviewTaskId || !reviewing) {
      return;
    }

    const intervalId = window.setInterval(async () => {
      try {
        const statusResult: ReviewTaskStatusResponse = await getReviewTaskStatus(reviewTaskId);
        setReviewProgress(statusResult.progress ?? 0);
        setReviewStatusMessage(statusResult.message || '正在解析合同...');

        if (statusResult.status === 'processing') {
          setThinkingSteps((prev) => {
            const next = [...prev];
            const nextLine = `[进度 ${statusResult.progress ?? 0}%] ${statusResult.message || '处理中...'}`;
            if (next[next.length - 1] !== nextLine) {
              next.push(nextLine);
            }
            return next.slice(-10);
          });
          return;
        }

        window.clearInterval(intervalId);

        if (statusResult.status === 'success' && statusResult.result) {
          setReviewResult(statusResult.result);
          setThinkingSteps((prev) => [...prev, `✅ 审查完成，发现 ${statusResult.result?.risks.length ?? 0} 个风险项`]);
          setReviewProgress(100);
          setReviewStatusMessage('审查完成');
        } else {
          const failMsg = statusResult.error || '任务执行失败';
          setError(failMsg);
          setThinkingSteps((prev) => [...prev, `❌ 审查失败: ${failMsg}`]);
          setReviewStatusMessage('审查失败');
        }

        setReviewing(false);
        setReviewTaskId('');
      } catch (pollErr: any) {
        window.clearInterval(intervalId);
        const msg = pollErr?.message || '状态查询失败';
        setError(msg);
        setThinkingSteps((prev) => [...prev, `❌ 审查失败: ${msg}`]);
        setReviewing(false);
        setReviewTaskId('');
      }
    }, 2000);

    return () => {
      window.clearInterval(intervalId);
    };
  }, [reviewTaskId, reviewing]);

  // 示例合同文本（硬编码）
  const DEMO_CONTRACT_TEXT = `
劳动合同

甲方（用人单位）：某某科技有限公司
乙方（劳动者）：张三

第一条 合同期限
本合同为固定期限劳动合同，期限为三年，自2024年1月1日起至2026年12月31日止。试用期为六个月。

第二条 工作内容和工作地点
1. 乙方同意根据甲方工作需要，从事软件开发工作。
2. **甲方有权根据业务需要单方面调整乙方的工作岗位和工作地点，乙方必须无条件服从。**
3. 工作地点：甲方指定的任何办公场所。

第三条 工作时间和休息休假
1. 实行标准工时制，每周工作五天，每天工作八小时。
2. **因工作需要，乙方应当服从甲方安排的加班，周末和节假日加班不另行支付加班费。**
3. 乙方每年享有带薪年休假5天。

第四条 劳动报酬
1. 乙方月工资为人民币8000元（税前）。
2. **试用期内不缴纳社会保险和住房公积金。**
3. **工资发放时间由甲方根据经营状况决定，可能延迟发放。**

第五条 社会保险和福利待遇
1. 甲方依法为乙方缴纳社会保险（试用期除外）。
2. **乙方因工负伤的，医疗费用由乙方自行承担50%。**

第六条 劳动纪律
1. 乙方应当遵守甲方的规章制度。
2. **乙方不得拒绝甲方安排的任何工作任务，否则视为严重违反劳动纪律。**
3. **乙方每月迟到或早退累计超过3次，甲方有权扣除当月全部工资。**

第七条 保密和竞业限制
1. **乙方在职期间及离职后五年内，不得从事与甲方相同或相似的业务。**
2. **违反竞业限制的，乙方应当向甲方支付违约金人民币50万元。**

第八条 合同的解除和终止
1. **乙方提前解除合同的，应当提前三个月书面通知甲方，并支付违约金人民币10万元。**
2. **甲方可以随时解除本合同，无需支付任何经济补偿。**

第九条 其他
1. 本合同一式两份，甲乙双方各执一份。
2. 本合同自双方签字盖章之日起生效。

甲方（盖章）：某某科技有限公司
乙方（签字）：张三
日期：2024年1月1日
  `.trim();

  const handleDemoContract = async () => {
    setError('');
    setThinkingSteps([]);
    setReviewResult(null);
    
    // 模拟文件上传成功
    const demoContractId = `demo_contract_${Date.now()}`;
    setContractId(demoContractId);
    setUploadResult({
      success: true,
      message: '示例合同已加载',
      contract_id: demoContractId,
      chunk_count: 1,
      text_length: DEMO_CONTRACT_TEXT.length
    });
    
    // 自动开始审查
    setTimeout(() => {
      handleDemoReview(demoContractId);
    }, 500);
  };

  const handleDemoReview = async (demoId: string) => {
    setReviewing(true);
    setError('');
    setThinkingSteps(['🚀 已提交审查任务，正在进入队列...']);
    setReviewResult(null);
    setReviewProgress(0);
    setReviewStatusMessage('任务排队中...');

    try {
      const submitResult = await reviewContract(demoId);
      setReviewTaskId(submitResult.task_id);
      setThinkingSteps((prev) => [...prev, `🧩 任务已创建: ${submitResult.task_id}`]);
    } catch (err: any) {
      const msg = err.message || '审查失败';
      setError(msg);
      setThinkingSteps((prev) => [...prev, `❌ 审查失败: ${msg}`]);
      setReviewing(false);
      setReviewTaskId('');
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      handleFileSelect(droppedFile);
    }
  };

  const handleFileSelect = (selectedFile: File) => {
    const validTypes = [
      'application/pdf',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'image/jpeg',
      'image/jpg',
      'image/png'
    ];
    
    if (!validTypes.includes(selectedFile.type)) {
      setError('仅支持 PDF、Word 文档和图像文件（JPG/PNG）');
      return;
    }

    setFile(selectedFile);
    setError('');
    setUploadResult(null);
    setReviewResult(null);
    setThinkingSteps([]);
  };

  const handleUpload = async () => {
    if (!file) return;

    setUploading(true);
    setError('');
    setThinkingSteps([]);

    try {
      const result = await uploadDocument(file);
      setUploadResult(result);
      setContractId(result.contract_id);
    } catch (err: any) {
      setError(err.message || '上传失败');
    } finally {
      setUploading(false);
    }
  };

  const handleReview = async () => {
    if (!contractId) return;

    setReviewing(true);
    setError('');
    setThinkingSteps(['🚀 已提交审查任务，正在进入队列...']);
    setReviewResult(null);
    setReviewProgress(0);
    setReviewStatusMessage('任务排队中...');

    try {
      const submitResult = await reviewContract(contractId);
      setReviewTaskId(submitResult.task_id);
      setThinkingSteps((prev) => [...prev, `🧩 任务已创建: ${submitResult.task_id}`]);
    } catch (err: any) {
      let errorMsg = err.message || '审查失败';

      if (errorMsg.includes('Rate limit') || errorMsg.includes('rate_limit_exceeded')) {
        errorMsg = 'API 速率限制：今日配额已用完。请等待约 10 分钟后重试，或更换 API Key。';
      } else if (errorMsg.includes('Failed to fetch')) {
        errorMsg = '无法连接到服务器，请确保后端服务已启动';
      }

      setError(errorMsg);
      setThinkingSteps((prev) => [...prev, `❌ 审查失败: ${errorMsg}`]);
      setReviewing(false);
      setReviewTaskId('');
    }
  };

  const getRiskStyle = (level: RiskLevel) => {
    switch (level) {
      case RiskLevel.HIGH:
        return {
          bg: 'bg-red-50 dark:bg-red-950/20',
          border: 'border-red-200 dark:border-red-900/50',
          text: 'text-red-700 dark:text-red-400',
          badge: 'bg-red-500',
          icon: '🚨',
        };
      case RiskLevel.MEDIUM:
        return {
          bg: 'bg-yellow-50 dark:bg-yellow-950/20',
          border: 'border-yellow-200 dark:border-yellow-900/50',
          text: 'text-yellow-700 dark:text-yellow-400',
          badge: 'bg-yellow-500',
          icon: '⚠️',
        };
      case RiskLevel.LOW:
        return {
          bg: 'bg-blue-50 dark:bg-blue-950/20',
          border: 'border-blue-200 dark:border-blue-900/50',
          text: 'text-blue-700 dark:text-blue-400',
          badge: 'bg-blue-500',
          icon: 'ℹ️',
        };
    }
  };

  return (
    <div className="mx-auto max-w-7xl p-6">
      <div className="mb-8">
        <h1 className="mb-2 font-serif text-4xl font-bold">智能合同审查</h1>
        <p className="text-muted-foreground">精准定位高风险条款，逐句穿透法律依据。</p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* 左侧：上传与思考链 */}
        <div className="space-y-6">
          {/* 文件上传区 */}
          <div className="card p-6">
            <h2 className="mb-4 flex items-center gap-2 text-xl font-semibold">
              <Upload size={20} />
              上传合同文档
            </h2>

            {/* 高级 Dropzone */}
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => document.getElementById('file-input')?.click()}
              className={`
                cursor-pointer rounded-lg border-2 border-dashed p-8 text-center transition-smooth
                ${isDragging 
                  ? 'border-primary bg-accent' 
                  : 'border-border hover:border-primary/50 hover:bg-accent/50'
                }
              `}
            >
              <FileText size={48} className="mx-auto mb-4 text-muted-foreground" />
              <p className="mb-2 font-medium text-foreground">
                拖拽文件到此处，或点击选择文件
              </p>
              <p className="text-sm text-muted-foreground">
                支持 PDF、Word、图像（JPG/PNG）
              </p>
              <input
                id="file-input"
                type="file"
                accept=".pdf,.docx,.doc,.jpg,.jpeg,.png"
                onChange={(e) => e.target.files?.[0] && handleFileSelect(e.target.files[0])}
                className="hidden"
              />
            </div>

            {/* 已选择的文件 */}
            {file && (
              <div className="mt-4 flex items-center justify-between rounded-lg bg-accent p-4">
                <div className="flex items-center gap-3">
                  <FileText size={20} className="text-primary" />
                  <div>
                    <p className="text-sm font-medium text-foreground">{file.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {(file.size / 1024).toFixed(2)} KB
                    </p>
                  </div>
                </div>
                <button
                  onClick={handleUpload}
                  disabled={uploading}
                  className="rounded-lg bg-gradient-legal px-4 py-2 text-sm font-medium transition-smooth hover:shadow-md disabled:cursor-not-allowed disabled:opacity-50 focus-ring"
                >
                  {uploading ? (
                    <span className="flex items-center gap-2 text-foreground dark:text-white">
                      <Loader2 size={16} className="animate-spin text-foreground dark:text-white" />
                      上传中...
                    </span>
                  ) : (
                    <span className="text-foreground dark:text-white">开始上传</span>
                  )}
                </button>
              </div>
            )}

            {/* 一键体验：示例合同 */}
            {!file && !uploadResult && (
              <div className="mt-6 border-t border-border pt-6">
                <button
                  onClick={handleDemoContract}
                  className="w-full rounded-lg border-2 border-dashed border-primary/50 bg-gradient-to-r from-amber-50 to-orange-50 dark:from-amber-950/20 dark:to-orange-950/20 p-6 text-left transition-smooth hover:border-primary hover:shadow-md"
                >
                  <div className="flex items-center gap-4">
                    <div className="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-full bg-gradient-legal">
                      <ScaleIcon size={24} className="text-foreground dark:text-white" />
                    </div>
                    <div className="flex-1">
                      <h3 className="mb-1 font-semibold text-foreground">✨ 一键体验：审查《高风险劳动合同示例》</h3>
                      <p className="text-sm text-muted-foreground">
                        无需上传文件，立即体验 AI 合同审查功能
                      </p>
                    </div>
                  </div>
                </button>
              </div>
            )}

            {/* 上传成功提示 */}
            {uploadResult && (
              <div className="mt-4 rounded-lg border border-green-200 bg-green-50 p-4 dark:border-green-900/50 dark:bg-green-950/20">
                <div className="flex items-start gap-3">
                  <CheckCircle size={20} className="mt-0.5 flex-shrink-0 text-green-600 dark:text-green-400" />
                  <div className="flex-1">
                    <p className="mb-2 font-medium text-green-700 dark:text-green-400">文件已成功入库</p>
                    <div className="space-y-1 text-sm text-green-600 dark:text-green-500">
                      <p>Contract ID: <span className="font-mono text-xs">{uploadResult.contract_id}</span></p>
                      <p>切片数量: <span>{uploadResult.chunk_count}</span></p>
                    </div>
                  </div>
                </div>
                
                <button
                  onClick={handleReview}
                  disabled={reviewing}
                  className="mt-4 flex w-full items-center justify-center gap-2 rounded-lg bg-gradient-legal px-6 py-3 font-medium shadow-lg transition-smooth hover:shadow-xl disabled:cursor-not-allowed disabled:opacity-50 focus-ring"
                >
                  {reviewing ? (
                    <span className="flex items-center gap-2 text-foreground dark:text-white">
                      <Loader2 size={20} className="animate-spin text-foreground dark:text-white" />
                      解析中 {reviewProgress}% · {reviewStatusMessage || '正在深度审查...'}
                    </span>
                  ) : (
                    <span className="flex items-center gap-2 text-foreground dark:text-white">
                      <ScaleIcon size={20} className="text-foreground dark:text-white" />
                      开始深度审查
                    </span>
                  )}
                </button>
              </div>
            )}

            {/* 错误提示 */}
            {error && (
              <div className="mt-4 flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-4 dark:border-red-900/50 dark:bg-red-950/20">
                <AlertCircle size={20} className="mt-0.5 flex-shrink-0 text-red-600 dark:text-red-400" />
                <p className="text-sm text-red-700 dark:text-red-400">{error}</p>
              </div>
            )}
          </div>

          {/* 思考链终端 */}
          {(reviewing || thinkingSteps.length > 0) && (
            <ThinkingTerminal steps={thinkingSteps} isActive={reviewing} />
          )}
        </div>

        {/* 右侧：风险报告区 */}
        <div className="space-y-6">
          {reviewResult && !reviewing && (
            <>
              {/* 整体评估 */}
              <div className="card p-6">
                <h2 className="mb-4 flex items-center gap-2 text-xl font-semibold">
                  <AlertTriangle size={20} className="text-yellow-500" />
                  整体风险评估
                </h2>
                <p className="mb-4 leading-relaxed">{reviewResult.overall_summary}</p>
                <div className="grid grid-cols-2 gap-4 border-t border-border pt-4">
                  <div className="text-center">
                    <div className="mb-1 text-3xl font-bold text-red-500">{reviewResult.risks.length}</div>
                    <div className="text-sm text-muted-foreground">风险项</div>
                  </div>
                  <div className="text-center">
                    <div className="mb-1 text-3xl font-bold text-primary">
                      {reviewResult.is_image_based ? '图像' : '文本'}
                    </div>
                    <div className="text-sm text-muted-foreground">识别模式</div>
                  </div>
                </div>
              </div>

              {/* 风险列表 */}
              <div className="space-y-4">
                <h2 className="text-xl font-semibold">风险详情</h2>
                {reviewResult.risks.map((risk, index) => {
                  const style = getRiskStyle(risk.risk_level);
                  return (
                    <div
                      key={index}
                      className={`space-y-4 rounded-lg border p-6 ${style.bg} ${style.border}`}
                    >
                      {/* 风险等级标签 */}
                      <div className="flex items-center justify-between">
                        <span className={`flex items-center gap-2 rounded-full px-3 py-1 text-sm font-medium text-white ${style.badge}`}>
                          <span>{style.icon}</span>
                          {risk.risk_level}
                        </span>
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-muted-foreground">置信度</span>
                          <span className={`text-sm font-bold ${style.text}`}>
                            {(risk.confidence_score * 100).toFixed(0)}%
                          </span>
                        </div>
                      </div>

                      {/* 原文条款 */}
                      <div>
                        <h4 className="mb-2 text-sm font-medium text-muted-foreground">📜 原文条款</h4>
                        <p className="rounded-lg bg-background/50 p-3 text-sm leading-relaxed">
                          {risk.original_clause}
                        </p>
                        {risk.original_text_quote && (
                          <p className="mt-2 text-xs text-muted-foreground">
                            关键引用: <span className={`font-medium ${style.text}`}>"{risk.original_text_quote}"</span>
                          </p>
                        )}
                      </div>

                      {/* 风险解释 */}
                      <div>
                        <h4 className="mb-2 text-sm font-medium text-muted-foreground">⚠️ 风险解释</h4>
                        <p className={`text-sm leading-relaxed ${style.text}`}>
                          {risk.risk_explanation}
                        </p>
                      </div>

                      {/* 法律依据 */}
                      {risk.legal_basis && risk.legal_basis.length > 0 && (
                        <div>
                          <h4 className="mb-2 text-sm font-medium text-muted-foreground">⚖️ 法律依据</h4>
                          <div className="space-y-2">
                            {risk.legal_basis.map((basis, idx) => (
                              <div key={idx} className="rounded-lg bg-background/50 p-3">
                                <p className="text-sm leading-relaxed">{basis}</p>
                                {risk.legal_basis_links && risk.legal_basis_links[idx] && (
                                  <a
                                    href={risk.legal_basis_links[idx]}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="mt-2 flex items-center gap-1 text-xs text-blue-600 hover:text-blue-500 dark:text-blue-400 dark:hover:text-blue-300"
                                  >
                                    <ExternalLink size={12} />
                                    查看法条原文
                                  </a>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* 修改建议 */}
                      <div>
                        <h4 className="mb-2 text-sm font-medium text-muted-foreground">💡 修改建议</h4>
                        <p className="rounded-lg bg-green-50 p-3 text-sm leading-relaxed text-green-700 dark:bg-green-950/30 dark:text-green-400">
                          {risk.revise_suggestion}
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </>
          )}

          {reviewing && !reviewResult && (
            <div className="card relative overflow-hidden p-8 text-center">
              <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(245,158,11,0.18),transparent_45%),radial-gradient(circle_at_80%_80%,rgba(249,115,22,0.15),transparent_40%)]" />
              <div className="relative z-10 mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-gradient-legal shadow-xl">
                <ScaleIcon size={28} className="text-white" withFire={true} />
              </div>
              <h3 className="relative z-10 mb-2 text-xl font-semibold">AI 正在解析合同</h3>
              <p className="relative z-10 mb-6 text-sm text-muted-foreground">{reviewStatusMessage || '正在深度审查条款风险，请稍候...'}</p>

              <div className="relative z-10 mx-auto h-3 w-full max-w-md overflow-hidden rounded-full bg-muted">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-amber-500 via-orange-500 to-red-500 transition-all duration-500"
                  style={{ width: `${Math.max(reviewProgress, 8)}%` }}
                />
              </div>
              <p className="relative z-10 mt-2 text-xs text-muted-foreground">进度 {reviewProgress}%</p>
            </div>
          )}

          {!reviewResult && !reviewing && (
            <div className="card p-12 text-center">
              <FileText size={64} className="mx-auto mb-4 text-muted-foreground/30" />
              <p className="font-medium text-foreground">上传合同并开始审查后，风险报告将显示在这里</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
