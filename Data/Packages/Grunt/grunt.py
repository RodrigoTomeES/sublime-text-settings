import os
import json
import subprocess
from hashlib import sha1

import sublime
import sublime_plugin

package_url = "https://github.com/sptndc/sublime-grunt"


class GruntRunner(object):
    def __init__(self, window):
        self.window = window
        self.list_gruntfiles()

    def list_tasks(self):
        try:
            self.callcount = 0
            json_result = self.fetch_json()
        except TypeError as e:
            self.window.new_file().run_command("grunt_error", {
                "message": "Grunt: JSON is malformed\n\n%s\n\n" % e
            })
            sublime.error_message("Could not read available tasks\n")
        else:
            tasks = [[name, task['info'], task['meta']['info']] for name, task in json_result.items()]
            return sorted(tasks, key=lambda task: task)

    def run_expose(self):
        package_path = os.path.join(sublime.packages_path(), 'Grunt')
        args = r'grunt --no-color --tasks "%s" expose:%s' % (package_path, os.path.basename(self.chosen_gruntfile))
        expose = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  env=get_env_with_exec_args_path(), cwd=self.wd, shell=True)
        (stdout, stderr) = expose.communicate()
        if 127 == expose.returncode:
            sublime.error_message("\"grunt\" command not found.\nPlease add Grunt's location to your PATH.")
            return

        return self.fetch_json()

    def fetch_json(self):
        json_file_name = os.path.join(self.wd, '.sublime-grunt.cache')
        data = None
        if os.path.exists(json_file_name):
            sha1 = hash_file(self.chosen_gruntfile)
            json_data = open(json_file_name)
            try:
                data = json.load(json_data)
                if data[self.chosen_gruntfile]["sha1"] == sha1:
                    return data[self.chosen_gruntfile]["tasks"]
            finally:
                json_data.close()

        self.callcount += 1
        if self.callcount == 1:
            return self.run_expose()

        if data is None:
            raise TypeError("Could not expose gruntfile")

        raise TypeError("Sha1 from grunt expose ({0}) is not equal to calculated ({1})".format(
            data[self.chosen_gruntfile]["sha1"], sha1
        ))

    def list_gruntfiles(self):
        # Load gruntfile paths from config
        self.file_paths = get_grunt_file_paths()
        self.folders = []
        self.grunt_files = []
        for f in self.window.folders():
            self.folders.append(f)

        for f in self.file_paths:
            if os.path.isabs(f):
                self.folders.append(f)
            else:
                self.folders += [
                    os.path.join(parent, f)
                    for parent in self.window.folders()
                    if os.path.exists(os.path.join(parent, f))
                ]

        for f in self.folders:
            if os.path.exists(os.path.join(f, "Gruntfile.js")):
                self.grunt_files.append(os.path.realpath(os.path.join(f, "Gruntfile.js")))
            elif os.path.exists(os.path.join(f, "Gruntfile.coffee")):
                self.grunt_files.append(os.path.realpath(os.path.join(f, "Gruntfile.coffee")))

        if len(self.grunt_files) > 0:
            if len(self.grunt_files) == 1:
                self.choose_file(0)
            else:
                self.window.show_quick_panel(self.grunt_files, self.choose_file)
        else:
            sublime.error_message("Gruntfile.js or Gruntfile.coffee not found!")

    def choose_file(self, file):
        # Fix quick panel was cancelled
        if file == -1:
            return

        self.wd = os.path.dirname(self.grunt_files[file])
        self.chosen_gruntfile = self.grunt_files[file]
        self.tasks = self.list_tasks()
        if self.tasks is not None:
            # Fix quick panel unavailable
            sublime.set_timeout(lambda: self.window.show_quick_panel(self.tasks, self.on_done), 1)

    def on_done(self, task):
        if task > -1:
            path = get_env_path()
            exec_args = {
                'cmd': "grunt --no-color " + self.tasks[task][0],
                'shell': True,
                'working_dir': self.wd,
                'path': path
            }
            self.window.run_command("exec", exec_args)


def hash_file(file_name):
    with open(file_name, mode='rb') as fn:
        file_hash = sha1()
        content = fn.read()
        file_hash.update(str("blob " + str(len(content)) + "\0").encode('UTF-8'))
        file_hash.update(content)
        return file_hash.hexdigest()


def get_env_path():
    path = os.environ['PATH']
    settings = sublime.load_settings('Grunt.sublime-settings')
    if settings:
        exec_args = settings.get('exec_args')
        if exec_args:
            path = exec_args.get('path', os.environ['PATH'])

    return str(path)


def get_grunt_file_paths():
    # Get the user settings
    global_settings = sublime.load_settings('Grunt.sublime-settings')
    # Check the settings for the current project
    # If there is a setting for the paths in the project, it takes precidence
    # No setting in the project, then use the global one
    # If there is no global one, then use a default
    return sublime.active_window().active_view().settings().get('Grunt', {}).get(
        'gruntfile_paths', global_settings.get('gruntfile_paths', [])
    )


def get_env_with_exec_args_path():
    env = os.environ.copy()
    settings = sublime.load_settings('Grunt.sublime-settings')
    if settings:
        exec_args = settings.get('exec_args')
        if exec_args:
            path = str(exec_args.get('path', ''))
            if path:
                env['PATH'] = path

    return env


class GruntCommand(sublime_plugin.WindowCommand):
    def run(self):
        GruntRunner(self.window)


class GruntKillCommand(sublime_plugin.WindowCommand):
    def run(self):
        self.window.run_command("exec", {"kill": True})


class GruntErrorCommand(sublime_plugin.TextCommand):
    def run(self, edit, **args):
        view = self.view
        prefix = "Please file an issue on " + package_url + "/issues and attach this output.\n\n"
        view.insert(edit, 0, prefix + args["message"])
