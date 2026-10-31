from pathlib import Path
status='''v2质量测量修订已准备上传，远端Python/Shell语法及3文件哈希核验通过。cloth_prim_view.py:408–424确认get_particle_masses底层为cloth tensor view.get_masses()。本地确认场景构造和仿真循环与v1完全一致；阳性、响应未达阈值和质量不匹配判读用例通过。

唯一下一步由用户执行 `bash /root/autodl-tmp/run-attachment-canary-v2.sh`。只补充逐粒子质量（0/120/180步）、质量加权质心和绕枢轴重力矩，不修改物理配置、模拟时长或0.05rad能力门槛。质量总和对USD0.021kg容差0.2%，起止数组须一致。重力矩不是附件实际传递力矩。旧版数据/脚本保留；本轮未启动GPU，正式成功0。

'''
for name in ['DAY4_NEXT_STEPS.md','DAY4_MINIMUM_PLAN.md']:
 p=Path(name);s=p.read_text(encoding='utf8');a=s.index('## 唯一下一步');z=s.index('## 最低完成顺序',a);p.write_text(s[:a]+'## 唯一下一步\n\n'+status+s[z:],encoding='utf8')
p=Path('DAY4_ACCEPTANCE_TRACKER.md');p.write_text('# v2质量测量已就绪\n\n'+status+p.read_text(encoding='utf8'),encoding='utf8')
Path('day4-actionchunk-test/constraint_api_review/V2_MASS_READBACK.md').write_text('# 短测试v2质量读回\n\n'+status+'\n若仍未达转动门槛，保留失败，不自动扫描参数。先分析质量读回、重力矩与实际运动，区分配置不符和同配置弱响应。脚本自动依序检查三组；任一运行、质量或既定能力关卡失败便停止并保存数据。\n',encoding='utf8')
