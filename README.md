# llm_flow_server 使用说明文档 (后端工程)

## 一.项目简介及门户地址

本项目是一款**在windows平台下面向本地化大语言模型部署的低代码开发平台**(LLM_FLOW)的后端服务,其对应前端项目地址如下所示. 项目采用Python+Vue3前后端分离架构. 平台通过**可视化流程编排**与**底层原理级节点控制**，实现快速搭建AI应用。核心目标是通过**流程计算与提示词工程的深度配合**，使消费级硬件上的小模型在特定任务中达到完全可用的效果. 项目的详细介绍以及使用说明文档请查看项目门户文档。

### 项目门户地址 ( 包含前后端项目地址, 项目介绍与使用说明 )

https://gitee.com/peach_pony/llm_flow_overview.git

### 前端项目地址

https://gitee.com/peach_pony/llm_flow_web.git

## 二.启动部署

如果需要使用显卡加速大模型推理,请预先配置好 CUDA 环境 (**推荐版本 12.1**) 推荐使用 conda 进行环境管理 (**推荐python版本3.10**)
**windows环境下项目启动方式如下**

1. 在项目更目录下执行命令 **conda env create -f environment.yml** 创建环境并安装依赖 

2. 执行命令 **pip install llama-cpp-python --prefer-binary --extra-index-url=https://abetlen.github.io/llama-cpp-python/whl/cu121/** 安装社区预编译llama.cpp (对应版本: llama-cpp 0.3.4,  cuda 12.1, 另外上述仓库中也提供其他 python + cuda 版本组合的 windows 预编译文件), 若使用纯 cpu 方案请自行编辑安装对应版本的 llama.cpp (未找到合适的社区资源库)
3. 使用 **python main.py** 启动后端项目
4. 启动对应的前端项目

## 三.节点开发文档

尚在完善中敬请期待