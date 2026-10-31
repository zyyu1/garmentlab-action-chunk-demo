from pathlib import Path
status='''短场景约束能力测试已准备、上传并完成远端Python/Shell语法及3文件SHA256核验。判读程序的合成阳性、有效阴性、无效附件记录测试通过；不能将这些静态检查称为物理验证。

下一步由用户执行 `bash /root/autodl-tmp/run-attachment-canary.sh`。依次独立进程运行rigid、disabled、enabled；每组180个1/120秒物理步，应用启动耗时另计。任一失败立即停止，保留完整日志/场景/轨迹/读回。助手收到完成后自动下载审查。当前未启动GPU，正式成功0。

'''
for name in ['DAY4_NEXT_STEPS.md','DAY4_MINIMUM_PLAN.md']:
 p=Path(name);s=p.read_text(encoding='utf8');a=s.index('## 唯一下一步');z=s.index('## 最低完成顺序',a);p.write_text(s[:a]+'## 唯一下一步\n\n'+status+s[z:],encoding='utf8')
p=Path('DAY4_ACCEPTANCE_TRACKER.md');p.write_text('# 2026-10-31 短测试已就绪\n\n'+status+p.read_text(encoding='utf8'),encoding='utf8')
p=Path('day4-actionchunk-test/constraint_api_review/API_REVIEW.md');s=p.read_text(encoding='utf8');a=s.index('## 状态');p.write_text(s[:a]+'## 状态\n\n'+status+'''## 预注册判读（脚本为准）

枢轴误差<5mm，>20mm中止；刚体对照1秒内转角>0.1rad且前0.5秒正y转角>0.05rad。关闭附件对照载体总转角<0.01rad，0.5秒内锚点高度下降>0.1m。开启附件前120步最大锚点误差<5mm，正y转角比关闭对照增加>0.05rad，关闭附件后0.5秒锚点下降>50mm且与载体目标分离>50mm。阈值仅诊断本合成场景，不是Day4折叠成功阈值，也不将阴性外推为API全局单向。

此测试采用独立小cloth矩形、载体质量20g、惯量每轴0.0001 kg m²、cloth总质量21g，无地面、载体无碰撞，粒子非粒子碰撞关闭。原GarmentLab参数/场景未改变。偏心刚体对照质心x=50mm，cloth两组载体质心=枢轴。合成cloth不是双层衣摆；测试通过仅允许进入下一抓取能力验证。
''',encoding='utf8')
