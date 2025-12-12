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

                # 修复点4

                page.snack_bar = ft.SnackBar(ft.Text("天数必须是数字"))

                page.snack_bar.open = True

                page.update()

                return

            days = int(days_str)

            # 【一加适配】强制类型转换

            new_task = {

                "id": str(datetime.now().timestamp()),

                "name": str(name),

                "days": int(days),

                "original_target": int(days),

                "created_at": str(datetime.now().strftime("%Y-%m-%d")),

                "last_interaction": str(datetime.now().strftime("%Y-%m-%d")),

                "checked_today": False

            }

            app_data["tasks"].append(new_task)

            save_data(app_data)

            # 强制刷新主页

            render_main_page(msg="创建成功", reload_from_disk=True)

        except Exception as e:

            traceback.print_exc()

            # 修复点5

            page.snack_bar = ft.SnackBar(ft.Text(f"创建崩溃: {e}"), bgcolor="red")

            page.snack_bar.open = True

            page.update()

    # ================= 4. UI 渲染 (修复报错版) =================

    def render_main_page(e=None, msg=None, reload_from_disk=False):

        try:

            if reload_from_disk:

                fresh_data = load_data()

                app_data.clear()

                app_data.update(fresh_data)

            page.clean()

            tasks_column = ft.Column(spacing=10)

            if not app_data["tasks"]:

                tasks_column.controls.append(

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

                    tasks_column.controls.append(card)

                except:

                    continue

            achievements_column = ft.Column(spacing=10)

            if app_data.get("achievements"):

                for ach in app_data["achievements"]:

                    try:

                        achievements_column.controls.append(

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

                achievements_column.controls.append(

                    ft.Container(

                        content=ft.Text("还没有成就，加油！", color="grey", size=16),

                        alignment=ft.alignment.center,

                        padding=50

                    )

                )

            # --- 3. 使用 Tabs 将两者整合 ---

            tabs = ft.Tabs(

                selected_index=0,

                animation_duration=300,

                tabs=[

                    ft.Tab(

                        text="进行中",

                        icon=ft.Icons.LIST,

                        content=ft.Container(content=tasks_column, padding=10)

                    ),

                    ft.Tab(

                        text="成就墙",

                        icon=ft.Icons.EMOJI_EVENTS,

                        content=ft.Container(content=achievements_column, padding=10)

                    ),

                ],

                # 注意：这里不加 expand=True，因为外层已经是 scroll="auto"

                # 让 Tabs 自然填充高度即可，防止冲突

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

                        ft.Container(

                            content=tabs,

                            padding=10,

                            expand=True

                        )

                    ], scroll="auto", expand=True)

                )

            )

            if msg:

                # 修复点6：这里也改回标准写法

                page.snack_bar = ft.SnackBar(ft.Text(msg))

                page.snack_bar.open = True

            page.update()

        except Exception as e:

            # 紧急避险：如果主页渲染崩了，直接用 print 或者简单的 add 显示

            page.clean()

            page.add(ft.Text(f"主页渲染失败: {e}", color="red"))
            page.update()
    def render_add_page(e=None):
        page.clean()
        page.floating_action_button = None
        # autofocus=False，防止一加手机键盘弹出卡死页面
        name_field = ft.TextField(label="任务名称", autofocus=False)
        days_field = ft.TextField(label="天数 (数字)", keyboard_type="number")
        def on_confirm(e):
            if not name_field.value or not days_field.value:
                return
            e.control.text = "保存中..."
            e.control.update()
            do_add_task(name_field.value, days_field.value)

        def on_cancel(e):

            render_main_page()

        page.add(
            ft.SafeArea(
                ft.Container(
                    padding=30,
                    content=ft.Column([

                        ft.Icon(ft.Icons.ADD_TASK, size=80, color="teal"),
                        ft.Container(height=20),
                        name_field,
                        ft.Container(height=20),
                        days_field,
                        ft.Container(height=40),
                        ft.Row([
                            ft.ElevatedButton("取消", on_click=on_cancel),
                            ft.ElevatedButton("创建", on_click=on_confirm, bgcolor="teal", color="white"),
                        ], alignment="center")
                    ], horizontal_alignment="center")
                )
            )
        )
        # 这里补一个 update 确保界面刷新
        page.update()
    render_main_page()
if __name__ == "__main__":
    ft.app(target=main)
