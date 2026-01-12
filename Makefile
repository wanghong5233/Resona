.PHONY: help up down restart logs logs-backend logs-redis shell-backend redis-cli db-shell migrate ps clean build build-backend test-backend

help: ## 显示帮助信息
	@echo "Resona 项目管理命令："
	@echo ""
	@echo "  up                  启动所有服务"
	@echo "  down                停止所有服务"
	@echo "  restart             重启所有服务"
	@echo "  logs                查看所有服务日志"
	@echo "  logs-backend        查看后端日志"
	@echo "  logs-redis          查看Redis日志"
	@echo "  shell-backend       进入后端容器"
	@echo "  redis-cli           进入Redis CLI"
	@echo "  ps                  查看服务状态"
	@echo "  build               重新构建所有镜像"
	@echo "  build-backend       重新构建后端镜像"
	@echo ""

up: ## 启动所有服务（Backend + Redis）
	docker-compose up -d
	@echo "服务已启动！"
	@echo "Backend API: http://localhost:8080"
	@echo "查看日志: make logs-backend"

up-dev: ## 启动开发环境（Backend + Redis + PostgreSQL）
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
	@echo "开发环境已启动（包含数据库）！"

down: ## 停止并清理所有容器
	docker-compose down
	@echo "服务已停止"

down-v: ## 停止并清理所有容器和数据卷
	docker-compose down -v
	@echo "服务和数据已清除"

restart: ## 重启所有服务
	docker-compose restart
	@echo "服务已重启"

logs: ## 查看所有服务日志
	docker-compose logs -f

logs-backend: ## 查看后端日志（实时）
	docker-compose logs -f backend

logs-redis: ## 查看 Redis 日志
	docker-compose logs -f redis

shell-backend: ## 进入后端容器
	docker-compose exec backend /bin/bash

redis-cli: ## 进入 Redis CLI
	docker-compose exec redis redis-cli

db-shell: ## 进入 PostgreSQL 数据库（仅 up-dev 后可用）
	docker-compose exec postgres psql -U resona -d resona

migrate: ## 执行数据库迁移（仅 up-dev 后可用）
	docker-compose exec backend alembic upgrade head

ps: ## 查看服务状态
	docker-compose ps

clean: ## 清理临时文件和缓存
	@echo "清理 Python 缓存..."
	@powershell -Command "Get-ChildItem -Path . -Directory -Recurse -Filter '__pycache__' | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue"
	@powershell -Command "Get-ChildItem -Path . -File -Recurse -Filter '*.pyc' | Remove-Item -Force -ErrorAction SilentlyContinue"
	@powershell -Command "Get-ChildItem -Path . -Directory -Recurse -Filter '.pytest_cache' | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue"
	@echo "清理完成"

test-backend: ## 运行后端单元测试
	docker-compose exec backend pytest tests/ -v

build: ## 重新构建所有镜像
	docker-compose build --no-cache

build-backend: ## 重新构建后端镜像
	docker-compose build --no-cache backend

