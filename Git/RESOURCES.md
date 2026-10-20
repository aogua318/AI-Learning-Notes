# Git Resources

## Knowledge

- [Pro Git（中文版，官方书，免费）](https://git-scm.com/book/zh/v2)
  最权威的 Git 系统教材。课程主要引用：1.3 快照模型、2.2 三区与 add/commit、2.5 远程仓库、3.1–3.2 分支与合并、3.6 变基与黄金法则。
- [Git 官方文档：git-push](https://git-scm.com/docs/git-push)
  查阅 `--force`、`--force-with-lease`、`--force-if-includes` 的精确语义；推送被拒时的第一手依据。
- [Git 官方文档：git-fetch / git-pull](https://git-scm.com/docs/git-fetch)
  分清 fetch（只更新远程跟踪分支）与 pull（fetch + merge/rebase）的边界。
- [GitHub Docs：About authentication to GitHub](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/about-authentication-to-github)
  PAT、SSH、GCM 的官方说明；GitHub 已移除密码推送。
- [GitHub Docs：About remote repositories](https://docs.github.com/en/get-started/getting-started-with-git/about-remote-repositories)
  `origin`、`upstream`、HTTPS/SSH 地址形态与远程仓库模型。
- [GitHub Skills](https://skills.github.com)
  GitHub 官方实战课；适合在学完本课程后做一次真实的 PR 闭环。
- [Oh Shit, Git!?!（中文）](https://ohshitgit.com/zh)
  常见「完蛋了」场景的救火手册：误提交、改错 message、reset 过头等。

## Wisdom (Communities)

- [Learn Git Branching（中文）](https://learngitbranching.js.org/?locale=zh_CN)
  高质量交互式分支练习场；merge/rebase 的可视化练手优先用它，不必在本仓库重复造模拟器。
- [GitHub Community Discussions](https://github.com/orgs/community/discussions)
  GitHub 官方社区；认证、远程仓库、PR 流程问题可搜索/提问。
- [Stack Overflow: git 标签](https://stackoverflow.com/questions/tagged/git)
  适合查具体报错；高票答案通常附有可复现命令，但需注意版本差异。

## Gaps

- 目前没有针对「公司内网 Git 服务 / 代理 / 自签名证书」的资源；如果后续需要，单独补充。
- 用户暂未表示要加入社区；如改变意向，再推荐本地用户组或线上社区。
