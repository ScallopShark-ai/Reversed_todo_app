import flet as ft

from datetime import datetime

import traceback

import time

def main(page: ft.Page):

    # ================= 1. 一加13 专属适配配置 =================

    page.title = "逆序打卡"

    page.theme_mode = "light"

    # 【修复白屏核心】安卓需要滚动容错

    page.scroll = "None"

    # 【适配挖孔屏】禁用默认 Padding，完全交给 SafeArea 控制

    page.padding = 0

    # 使用系统默认字体，确保在 OPPO 手机上绝对能显示

    page.theme = ft.Theme()

    # ================= 2. 数据层 (强壮版) =================

    def load_data():

        """从手机存储读取数据"""

        try:

            data = page.client_storage.get("daka_data")

            if data is None:

                return {"tasks": [], "achievements": []}

            return data

        except Exception as e:

            print(f">>> 读取出错: {e}")

            return {"tasks": [], "achievements": []}

    def save_data(data):

        """保存数据到闪存"""

        try:

            page.client_storage.set("daka_data", data)

        except Exception as e:

            # 修复点1：改回标准的 SnackBar 写法

            page.snack_bar = ft.SnackBar(

                ft.Text(f"存储失败 (请检查权限): {str(e)}"),

                bgcolor="red",

                duration=5000

            )

            page.snack_bar.open = True

            page.update()

    # 初始化数据

    app_data = load_data()

    # --- 跨天检查逻辑 ---

    def process_penalty_logic():

        try:

            today_str = datetime.now().strftime("%Y-%m-%d")

            today_date = datetime.strptime(today_str, "%Y-%m-%d")

            data_changed = False

            for task in app_data["tasks"]:

                last_inter_str = task.get("last_interaction", today_str)

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

                    task['checked_today'] = False

                    task['last_interaction'] = today_str

                    data_changed = True

            if data_changed:

                save_data(app_data)

        except Exception:

            pass

    process_penalty_logic()

    # ================= 3. 业务逻辑 =================

    def get_day_color(days):

        if days < 5: return "green"

        elif days < 10: return "blue"

        return "black"

    def do_check_in(task_id):

        try:

            for task in app_data["tasks"]:

                if task['id'] == task_id:

                    task['days'] -= 1

                    if task['days'] <= 0:

                        app_data["tasks"].remove(task)

                        app_data["achievements"].append({

                            "name": task['name'],

                            "created_at": task.get('created_at', '?'),

                            "finished_at": datetime.now().strftime("%Y-%m-%d")

                        })

                        # 修复点2：改回标准的 SnackBar 写法

                        page.snack_bar = ft.SnackBar(ft.Text(f"任务 {task['name']} 完成！"))

                        page.snack_bar.open = True

                        page.update()

                    else:

                        task['checked_today'] = True

                        task['last_interaction'] = datetime.now().strftime("%Y-%m-%d")

                    save_data(app_data)

                    render_main_page(reload_from_disk=True)

                    break

        except Exception as e:

            # 修复点3

            page.snack_bar = ft.SnackBar(ft.Text(f"打卡错误: {e}"), bgcolor="red")

            page.snack_bar.open = True

            page.update()

    def do_add_task(name, days_str):
        try:
            if not days_str.isdigit():
                page.snack_bar = ft.SnackBar(ft.Text("天数必须是数字"))
                page.snack_bar.open = True
                page.update()
                return

            # --- 关键修改：先在内存中构建对象 ---
            new_task = {
                "id": str(datetime.now().timestamp()),
                "name": str(name),
                "days": int(days_str),
                "original_target": int(days_str),
                "created_at": datetime.now().strftime("%Y-%m-%d"),
                "last_interaction": datetime.now().strftime("%Y-%m-%d"),
                "checked_today": False
            }
            
            # 1. 先更新内存
            app_data["tasks"].append(new_task)
            
            # 2. 尝试保存 (即使保存失败，内存里也有数据，界面能显示出来)
            save_data(app_data)

            # 3. 渲染主页
            # 【核心修复】这里千万不要 reload_from_disk=True，否则会覆盖掉刚加进内存的任务
            render_main_page(msg="创建成功", reload_from_disk=False)

        except Exception as e:
            traceback.print_exc()
            # 如果出错，不要跳转页面，停留在当前页显示错误
            page.snack_bar = ft.SnackBar(
                ft.Text(f"创建失败: {e}"), 
                bgcolor="red",
                duration=5000 # 显示久一点
            )
            page.snack_bar.open = True
            page.update()

        
   # ================= 4. UI 渲染 (修复白屏版) =================

    def render_main_page(e=None, msg=None, reload_from_disk=False):
        try:
            if reload_from_disk:
                fresh_data = load_data()
                app_data.clear()
                app_data.update(fresh_data)

            page.clean()

            # 【改动1】使用 ListView 替代 Column，并开启 expand=True
            # ListView 自带滚动且性能更好，expand=True 让它在 Tab 内部撑满
            tasks_list = ft.ListView(expand=True, spacing=10)

            if not app_data["tasks"]:
                tasks_list.controls.append(
                    ft.Container(
                        content=ft.Text("暂无任务，点 + 号创建", color="grey", size=16),
                        alignment=ft.alignment.center,
                        padding=50
                    )
                )

            today_str = datetime.now().strftime("%Y-%m-%d")

            for task in app_data["tasks"]:
                try:
                    t_id = task.get('id')
                    t_name = str(task.get('name', '任务'))
                    t_days = task.get('days', 0)
                    is_done = task.get("checked_today", False) and task.get("last_interaction") == today_str

                    def on_click_checkin(e, t_id=t_id):
                        do_check_in(t_id)

                    card = ft.Card(
                        elevation=2,
                        content=ft.Container(
                            padding=15,
                            content=ft.Row([
                                ft.Column([
                                    ft.Text(t_name, size=18, weight="bold"),
                                    ft.Text(f"剩余 {t_days} 天", color=get_day_color(t_days))
                                ], expand=True),
                                ft.ElevatedButton(
                                    "已完成" if is_done else "打卡",
                                    disabled=is_done,
                                    bgcolor="grey" if is_done else "teal",
                                    color="white",
                                    on_click=on_click_checkin
                                )
                            ])
                        )
                    )
                    tasks_list.controls.append(card)
                except:
                    continue

            # 【改动2】同样将成就墙改为 ListView
            achievements_list = ft.ListView(expand=True, spacing=10)

            if app_data.get("achievements"):
                for ach in app_data["achievements"]:
                    try:
                        achievements_list.controls.append(
                            ft.Card(
                                elevation=1,
                                content=ft.ListTile(
                                    leading=ft.Icon(ft.Icons.EMOJI_EVENTS, color="amber"),
                                    title=ft.Text(f"{ach.get('name','未知')}", weight="bold"),
                                    subtitle=ft.Text(f"完成于: {ach.get('finished_at','?')}", size=12),
                                )
                            )
                        )
                    except:
                        continue
            else:
                achievements_list.controls.append(
                    ft.Container(
                        content=ft.Text("还没有成就，加油！", color="grey", size=16),
                        alignment=ft.alignment.center,
                        padding=50
                    )
                )

            # --- 3. Tabs 整合 ---
            tabs = ft.Tabs(
                selected_index=0,
                animation_duration=300,
                expand=True, # 【关键】让 Tabs 撑满剩余空间
                tabs=[
                    ft.Tab(
                        text="进行中",
                        icon=ft.Icons.LIST,
                        # Container 不设高度，由内部 ListView 撑开
                        content=ft.Container(content=tasks_list, padding=10)
                    ),
                    ft.Tab(
                        text="成就墙",
                        icon=ft.Icons.EMOJI_EVENTS,
                        content=ft.Container(content=achievements_list, padding=10)
                    ),
                ],
            )

            page.floating_action_button = ft.FloatingActionButton(
                icon="add", bgcolor="teal", on_click=render_add_page
            )

            page.add(
                ft.SafeArea(
                    ft.Column([
                        ft.Container(height=10),
                        ft.Text("  逆序打卡", size=28, weight="bold", color="teal"),
                        ft.Divider(),
                        # 直接放入 tabs，它会自动 expand
                        tabs
                    ], 
                    # 【核心修复】外层 Column 禁止滚动，强制撑满屏幕
                    scroll=None, 
                    expand=True)
                )
            )

            if msg:
                page.snack_bar = ft.SnackBar(ft.Text(msg))
                page.snack_bar.open = True
            page.update()

        except Exception as e:
            page.clean()
            # 这里的 scroll="auto" 没关系，因为是错误页面
            page.add(ft.Column([ft.Text(f"主页渲染失败: {e}", color="red")], scroll="auto"))
            page.update()
    def render_add_page(e=None):
        page.clean()
        page.floating_action_button = None
        
        name_field = ft.TextField(label="任务名称", autofocus=False)
        days_field = ft.TextField(label="天数 (数字)", keyboard_type="number")

        def on_confirm(e):
            if not name_field.value or not days_field.value:
                page.snack_bar = ft.SnackBar(ft.Text("请填写完整信息"))
                page.snack_bar.open = True
                page.update()
                return
                
            # 给用户一点反馈，防止连点
            e.control.text = "保存中..."
            e.control.disabled = True
            e.control.update()
            
            # 稍微延迟一下，给 UI 线程喘息时间（可选，但在某些安卓机上有奇效）
            time.sleep(0.1) 
            
            do_add_task(name_field.value, days_field.value)

        def on_cancel(e):
            render_main_page()

        # 【修复】外层容器必须可以滚动，否则键盘弹出会遮挡或导致点击无效
        page.add(
            ft.SafeArea(
                ft.Column([
                    ft.Container(height=20), # 顶部留白
                    ft.Icon(ft.Icons.ADD_TASK, size=80, color="teal"),
                    ft.Container(height=20),
                    name_field,
                    ft.Container(height=20),
                    days_field,
                    ft.Container(height=40),
                    ft.Row([
                        ft.ElevatedButton("取消", on_click=on_cancel),
                        ft.ElevatedButton("创建", on_click=on_confirm, bgcolor="teal", color="white"),
                    ], alignment="center"),
                    # 底部增加留白，防止被键盘顶死
                    ft.Container(height=300) 
                ], 
                horizontal_alignment="center",
                scroll="auto") # 【关键】允许滚动
            )
        )
        page.update()
    render_main_page()
if __name__ == "__main__":
    ft.app(target=main)
