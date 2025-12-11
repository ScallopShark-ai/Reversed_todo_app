import flet as ft
from datetime import datetime
import os
import traceback # 用于捕获错误

def main(page: ft.Page):
    # ================= 1. 基础配置 =================
    # 字体逻辑
    font_name = "my_font"
    font_path = "msyh.ttc"
    if not os.path.exists(font_path):
        font_path = "msyh.ttf"
    
    if os.path.exists(font_path):
        page.fonts = {font_name: font_path}
        page.theme = ft.Theme(font_family=font_name)
    else:
        page.theme = ft.Theme()

    page.title = "逆序打卡"
    page.theme_mode = "light"
    page.scroll = "None"
    
    # 【修复UI靠上】禁用页面默认内边距，完全由 SafeArea 控制
    page.padding = 0 

    # ================= 2. 数据处理 =================
    def load_data():
        try:
            data = page.client_storage.get("daka_data")
            if data is None:
                return {"tasks": [], "achievements": []}
            return data
        except:
            return {"tasks": [], "achievements": []}

    def save_data(data):
        try:
            page.client_storage.set("daka_data", data)
        except:
            pass

    app_data = load_data()

    # --- 跨天惩罚逻辑 ---
    def process_penalty_logic():
        try:
            today_str = datetime.now().strftime("%Y-%m-%d")
            today_date = datetime.strptime(today_str, "%Y-%m-%d")
            data_changed = False
            for task in app_data["tasks"]:
                last_inter_str = task.get("last_interaction", today_str)
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
                    task['checked_today'] = False
                    task['last_interaction'] = today_str
                    data_changed = True
            if data_changed:
                save_data(app_data)
        except:
            pass

    process_penalty_logic()

    # ================= 3. 业务逻辑 =================
    
    def get_day_color(days):
        if days < 5: return "green"
        elif days < 10: return "blue"
        return "black"

    # 打卡
    def do_check_in(task_id):
        for task in app_data["tasks"]:
            if task['id'] == task_id:
                task['days'] -= 1
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
                    task['checked_today'] = True
                    task['last_interaction'] = datetime.now().strftime("%Y-%m-%d")
                
                save_data(app_data)
                render_main_page()
                break

    # 添加任务 (带错误处理)
    # 添加任务 (修改版)
    def do_add_task(name, days_str):
        try:
            if not days_str.isdigit():
                page.snack_bar = ft.SnackBar(ft.Text("天数必须是纯数字！"))
                page.snack_bar.open = True
                page.update()
                return

            days = int(days_str)
            
            new_task = {
                "id": str(datetime.now().timestamp()),
                "name": name,
                "days": days,
                "original_target": days,
                "created_at": datetime.now().strftime("%Y-%m-%d"),
                "last_interaction": datetime.now().strftime("%Y-%m-%d"),
                "checked_today": False
            }
            app_data["tasks"].append(new_task)
            save_data(app_data)
            
            # 【核心修改点】这里不再直接弹窗，而是调用主页函数并传递消息
            render_main_page(msg="任务创建成功！")
            
        except Exception as e:
            # 出错时可以直接弹，因为没有页面跳转
            page.snack_bar = ft.SnackBar(ft.Text(f"创建失败: {str(e)}"))
            page.snack_bar.open = True
            page.update()

    # ================= 4. UI 渲染 (加入 SafeArea) =================
    
    # --- 场景 A: 主页 ---
    # --- 场景 A: 主页 (修改版) ---
    # 增加 msg 参数，默认为 None
    def render_main_page(e=None, msg=None):
        try:
            page.clean()
            
            # ... (这中间的 任务列表构建 代码保持不变，省略以节省空间) ...
            # ... (请保留你原有的 tasks_column, achievements_column, tabs 构建代码) ...
            
            # 这里为了完整性，我把省略号还原成你之前的关键结构，你需要确保中间逻辑还在：
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
            for task in app_data["tasks"]:
                # ... (保留你原来的循环逻辑) ...
                is_done_today = task.get("checked_today", False) and task.get("last_interaction") == today_str
                btn_text = "已完成" if is_done_today else "打卡"
                btn_bg = "grey" if is_done_today else "teal"
                
                # 闭包修复：需要在循环中绑定变量，否则点击所有按钮都会响应最后一个
                def on_click_checkin(e, t_id=task['id']):
                    do_check_in(t_id)

                task_card = ft.Card(
                    elevation=2,
                    content=ft.Container(
                        height=90,
                        padding=ft.padding.symmetric(horizontal=15),
                        content=ft.Stack(
                            controls=[
                                ft.Container(
                                    content=ft.Text(str(task['name']), size=16, weight="bold", max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                    alignment=ft.alignment.center_left,
                                    width=100,
                                ),
                                ft.Container(
                                    content=ft.Row(
                                        [
                                            ft.Text(str(task['days']), size=42, weight="bold", color=get_day_color(task['days'])),
                                            ft.Container(content=ft.Text("天", size=14, color="grey"), padding=ft.padding.only(top=14))
                                        ],
                                        alignment=ft.MainAxisAlignment.CENTER, spacing=2, tight=True
                                    ),
                                    alignment=ft.alignment.center,
                                ),
                                ft.Container(
                                    content=ft.ElevatedButton(text=btn_text, disabled=is_done_today, bgcolor=btn_bg, color="white", width=85, style=ft.ButtonStyle(padding=5), on_click=on_click_checkin),
                                    alignment=ft.alignment.center_right
                                )
                            ]
                        )
                    )
                )
                tasks_column.controls.append(task_card)

            # 成就墙逻辑保持不变
            achievements_column = ft.Column(spacing=10, scroll="auto")
            for ach in app_data["achievements"]:
                created_at = ach.get('created_at', '?')
                finished_at = ach.get('finished_at', '?')
                achievements_column.controls.append(
                    ft.ListTile(
                        leading=ft.Icon("emoji_events", color="amber"),
                        title=ft.Text(f"{ach['name']}", weight="bold"),
                        subtitle=ft.Text(f"周期: {created_at} 至 {finished_at}", size=12),
                    )
                )

            tabs = ft.Tabs(
                selected_index=0,
                tabs=[
                    ft.Tab(text="进行中", icon="list", content=ft.Container(content=tasks_column, padding=10)),
                    ft.Tab(text="成就墙", icon="emoji_events", content=ft.Container(content=achievements_column, padding=10)),
                ],
                expand=1,
            )

            page.add(
                ft.SafeArea(
                    ft.Container(
                        content=tabs,
                        padding=10
                    )
                )
            )
            
            page.floating_action_button = ft.FloatingActionButton(icon="add", bgcolor="teal", on_click=render_add_page)
            
            # 【核心修改点】在这里处理消息弹窗
            # 在 UI 控件全部 add 之后，update 之前，设置 SnackBar
            if msg:
                page.snack_bar = ft.SnackBar(ft.Text(msg))
                page.snack_bar.open = True
            
            page.update()
            
        except Exception as e:
            # 捕获主页渲染的错误，防止白屏死得不明不白
            print(traceback.format_exc())
            page.add(ft.Text(f"渲染错误: {e}", color="red"))
            page.update()

    # --- 场景 B: 添加页 ---
    def render_add_page(e=None):
        page.clean()
        page.floating_action_button = None
        
        name_field = ft.TextField(label="任务名称", autofocus=True)
        # 【小优化】设置 input_border_radius 让输入框圆润点，适合手机
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
            
            # 调用逻辑
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
            scroll="auto" # 允许内容滚动
        )
        # 【核心修复1】同样使用 SafeArea 包裹添加页
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

    render_main_page()

if __name__ == "__main__":
    ft.app(target=main)
