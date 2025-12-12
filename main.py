import flet as ft
from datetime import datetime
import os
import traceback

def main(page: ft.Page):
    
    # ================= 1. 基础配置 =================
    # 尝试加载中文字体，防止中文乱码（如果你有打包字体文件的话）
    font_name = "my_font"
    font_path = "msyh.ttc"
    if not os.path.exists(font_path):
        font_path = "msyh.ttf"
    
    if os.path.exists(font_path):
        page.fonts = {font_name: font_path}
        page.theme = ft.Theme(font_family=font_name)
    else:
        page.theme = ft.Theme() # 使用默认字体

    page.title = "逆序打卡"
    page.theme_mode = "light"
    page.scroll = "None"
    # 禁用默认 Padding，完全交给 SafeArea 控制，适配刘海屏
    page.padding = 0 

    # ================= 2. 数据层 (最核心的修复) =================
    
    def load_data():
        """安全读取数据，如果读取失败返回空结构"""
        try:
            data = page.client_storage.get("daka_data")
            if data is None:
                return {"tasks": [], "achievements": []}
            return data
        except Exception as e:
            print(f">>> 读取数据出错: {e}")
            return {"tasks": [], "achievements": []}

    def save_data(data):
        """保存数据，如果失败直接弹窗报错"""
        try:
            page.client_storage.set("daka_data", data)
        except Exception as e:
            # 🚨 严重错误直接弹窗
            print(f">>> 保存失败: {e}")
            page.snack_bar = ft.SnackBar(
                ft.Text(f"保存失败: {str(e)}"), 
                bgcolor="red",
                duration=5000
            )
            page.snack_bar.open = True
            page.update()
            raise e # 继续抛出异常，中断后续操作

    # 初始化内存数据
    app_data = load_data()

    # --- 跨天惩罚逻辑 ---
    def process_penalty_logic():
        try:
            today_str = datetime.now().strftime("%Y-%m-%d")
            today_date = datetime.strptime(today_str, "%Y-%m-%d")
            data_changed = False
            
            # 遍历检查是否漏打卡
            for task in app_data["tasks"]:
                last_inter_str = task.get("last_interaction", today_str)
                # 容错：防止旧数据里没有 last_interaction
                if not last_inter_str: last_inter_str = today_str
                
                last_date = datetime.strptime(last_inter_str, "%Y-%m-%d")
                delta_days = (today_date - last_date).days
                
                if delta_days > 0:
                    penalty = 0
                    if not task.get("checked_today", False):
                        penalty += 1
                    if delta_days > 1:
                        penalty += (delta_days - 1)
                    
                    if penalty > 0:
                        task['days'] += penalty
                        data_changed = True
                    
                    # 重置状态
                    task['checked_today'] = False
                    task['last_interaction'] = today_str
                    data_changed = True
            
            if data_changed:
                save_data(app_data)
        except Exception as e:
            print(f">>> 惩罚逻辑出错: {e}")

    process_penalty_logic()

    # ================= 3. 业务逻辑 =================
    
    def get_day_color(days):
        if days < 5: return "green"
        elif days < 10: return "blue"
        return "black"

    # 打卡逻辑
    def do_check_in(task_id):
        try:
            for task in app_data["tasks"]:
                if task['id'] == task_id:
                    task['days'] -= 1
                    
                    # 任务完成
                    if task['days'] <= 0:
                        app_data["tasks"].remove(task)
                        app_data["achievements"].append({
                            "name": task['name'],
                            "target": task.get('original_target', 0),
                            "created_at": task.get('created_at', datetime.now().strftime("%Y-%m-%d")),
                            "finished_at": datetime.now().strftime("%Y-%m-%d")
                        })
                        page.snack_bar = ft.SnackBar(ft.Text(f"恭喜！任务 {task['name']} 已完成！"))
                        page.snack_bar.open = True
                    else:
                        # 正常打卡
                        task['checked_today'] = True
                        task['last_interaction'] = datetime.now().strftime("%Y-%m-%d")
                    
                    save_data(app_data)
                    render_main_page() # 刷新界面
                    break
        except Exception as e:
            page.snack_bar = ft.SnackBar(ft.Text(f"打卡出错: {e}"), bgcolor="red")
            page.snack_bar.open = True
            page.update()

    # 添加任务 (修复版：强制类型转换 + 强制刷新)
    def do_add_task(name, days_str):
        try:
            if not days_str.isdigit():
                page.snack_bar = ft.SnackBar(ft.Text("天数必须是纯数字！"))
                page.snack_bar.open = True
                page.update()
                return

            days = int(days_str)
            
            # 【安全锁】强制把所有数据转为基础类型，防止 JSON 序列化失败
            new_task = {
                "id": str(datetime.now().timestamp()), # 唯一ID
                "name": str(name),
                "days": int(days),
                "original_target": int(days),
                "created_at": str(datetime.now().strftime("%Y-%m-%d")),
                "last_interaction": str(datetime.now().strftime("%Y-%m-%d")),
                "checked_today": False
            }
            
            # 1. 更新内存
            app_data["tasks"].append(new_task)
            
            # 2. 保存硬盘 (如果失败会弹窗)
            save_data(app_data)
            
            # 3. 【关键】跳转回主页，并命令主页从硬盘重读数据
            render_main_page(msg="任务创建成功！", reload_from_disk=True)
            
        except Exception as e:
            traceback.print_exc()
            page.snack_bar = ft.SnackBar(ft.Text(f"创建流程崩溃: {str(e)}"), bgcolor="red")
            page.snack_bar.open = True
            page.update()

    # ================= 4. UI 渲染 =================
    
    # --- 场景 A: 主页 ---
    # reload_from_disk: 是否强制从硬盘同步数据 (解决"存了但不显示"的问题)
    def render_main_page(e=None, msg=None, reload_from_disk=False):
        try:
            # 如果要求重读，则清空内存，从硬盘加载最新数据
            if reload_from_disk:
                print(">>> 正在从硬盘同步最新数据...")
                fresh_data = load_data()
                app_data.clear()
                app_data.update(fresh_data)

            page.clean()
            
            # 构建任务列表
            tasks_column = ft.Column(spacing=10, scroll="auto")
            
            if not app_data["tasks"]:
                tasks_column.controls.append(
                    ft.Container(
                        content=ft.Text("暂无任务，请点击右下角 + 号", color="grey", size=16),
                        alignment=ft.alignment.center,
                        padding=20
                    )
                )

            today_str = datetime.now().strftime("%Y-%m-%d")
            
            # 【容错渲染】即使某一个任务数据坏了，也不要让整个页面白屏
            for task in app_data["tasks"]:
                try:
                    # 获取数据，使用 .get 防止缺字段报错
                    t_id = task.get('id')
                    t_name = str(task.get('name', '未知任务'))
                    t_days = task.get('days', 0)
                    
                    is_done_today = task.get("checked_today", False) and task.get("last_interaction") == today_str
                    btn_text = "已完成" if is_done_today else "打卡"
                    btn_bg = "grey" if is_done_today else "teal"
                    
                    # 闭包绑定 ID
                    def on_click_checkin(e, t_id=t_id):
                        do_check_in(t_id)

                    task_card = ft.Card(
                        elevation=2,
                        content=ft.Container(
                            height=90,
                            padding=ft.padding.symmetric(horizontal=15),
                            content=ft.Stack(
                                controls=[
                                    # 左边：任务名
                                    ft.Container(
                                        content=ft.Text(t_name, size=16, weight="bold", max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                        alignment=ft.alignment.center_left,
                                        width=100,
                                    ),
                                    # 中间：天数
                                    ft.Container(
                                        content=ft.Row(
                                            [
                                                ft.Text(str(t_days), size=42, weight="bold", color=get_day_color(t_days)),
                                                ft.Container(content=ft.Text("天", size=14, color="grey"), padding=ft.padding.only(top=14))
                                            ],
                                            alignment=ft.MainAxisAlignment.CENTER, spacing=2, tight=True
                                        ),
                                        alignment=ft.alignment.center,
                                    ),
                                    # 右边：按钮
                                    ft.Container(
                                        content=ft.ElevatedButton(text=btn_text, disabled=is_done_today, bgcolor=btn_bg, color="white", width=85, style=ft.ButtonStyle(padding=5), on_click=on_click_checkin),
                                        alignment=ft.alignment.center_right
                                    )
                                ]
                            )
                        )
                    )
                    tasks_column.controls.append(task_card)
                except Exception as task_err:
                    print(f">>> 跳过损坏任务: {task_err}")
                    continue

            # 构建成就墙
            achievements_column = ft.Column(spacing=10, scroll="auto")
            if "achievements" in app_data:
                for ach in app_data["achievements"]:
                    achievements_column.controls.append(
                        ft.ListTile(
                            leading=ft.Icon("emoji_events", color="amber"),
                            title=ft.Text(f"{ach.get('name','未知')}", weight="bold"),
                            subtitle=ft.Text(f"周期: {ach.get('created_at','?')} 至 {ach.get('finished_at','?')}", size=12),
                        )
                    )

            # Tab 页签
            tabs = ft.Tabs(
                selected_index=0,
                tabs=[
                    ft.Tab(text="进行中", icon="list", content=ft.Container(content=tasks_column, padding=10)),
                    ft.Tab(text="成就墙", icon="emoji_events", content=ft.Container(content=achievements_column, padding=10)),
                ],
                expand=1,
            )

            # 页面组装 (使用 SafeArea 防止刘海遮挡)
            page.add(
                ft.SafeArea(
                    ft.Container(
                        content=tabs,
                        padding=10
                    )
                )
            )
            
            page.floating_action_button = ft.FloatingActionButton(icon="add", bgcolor="teal", on_click=render_add_page)
            
            # 显示消息提示
            if msg:
                page.snack_bar = ft.SnackBar(ft.Text(msg))
                page.snack_bar.open = True
            
            page.update()
            
        except Exception as e:
            print(traceback.format_exc())
            page.clean()
            page.add(ft.Text(f"主页渲染严重错误: {e}", color="red"))
            page.update()

    # --- 场景 B: 添加页 ---
    def render_add_page(e=None):
        page.clean()
        page.floating_action_button = None
        
        # autofocus=False 防止手机键盘自动弹出遮挡视图
        name_field = ft.TextField(label="任务名称", autofocus=False) 
        days_field = ft.TextField(label="目标天数 (纯数字)", keyboard_type="number")

        def on_confirm(e):
            if not name_field.value:
                name_field.error_text = "请输入任务名称"
                page.update()
                return
            if not days_field.value:
                days_field.error_text = "请输入目标天数"
                page.update()
                return
            
            # 按钮视觉反馈
            e.control.text = "正在保存..."
            e.control.bgcolor = "orange"
            e.control.update()

            do_add_task(name_field.value, days_field.value)

        def on_cancel(e):
            render_main_page()
            
        content_column = ft.Column(
            [
                ft.Icon(ft.Icons.ADD_TASK, size=64, color="teal"),
                ft.Container(height=20),
                ft.Text("新建挑战", size=24, weight="bold"),
                ft.Container(height=30),
                name_field,
                ft.Container(height=10),
                days_field,
                ft.Container(height=40),
                ft.Row([
                    ft.ElevatedButton("取消", on_click=on_cancel, bgcolor="grey", color="white", width=120, height=50),
                    ft.ElevatedButton("确定创建", on_click=on_confirm, bgcolor="teal", color="white", width=120, height=50),
                ], alignment="center", spacing=20)
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            scroll="auto"
        )
        
        page.add(
            ft.SafeArea(
                ft.Container(
                    content=content_column,
                    padding=20,
                    alignment=ft.alignment.center,
                    expand=True
                )
            )
        )
        page.update()

    # 启动应用
    render_main_page()

if __name__ == "__main__":
    ft.app(target=main)
