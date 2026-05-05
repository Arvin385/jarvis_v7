#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/wait.h>
#include <limits.h>

#define JARVIS_MAX_INPUT 4096
#define JSON_SIZE 8192

int debug = 0;
// -------------------------
// Escape JSON safely
// -------------------------
void escape_json(char *dst, const char *src, int max) {
    int j = 0;

    for (int i = 0; src[i] && j < max - 2; i++) {
        char c = src[i];

        if (c == '"' || c == '\\') {
            dst[j++] = '\\';
            dst[j++] = c;
        } 
        else if (c == '\n') {
            dst[j++] = '\\';
            dst[j++] = 'n';
        } 
        else if (c == '\r') {
            dst[j++] = '\\';
            dst[j++] = 'r';
        } 
        else if (c == '\t') {
            dst[j++] = '\\';
            dst[j++] = 't';
        } 
        else {
            dst[j++] = c;
        }
    }

    dst[j] = '\0';
}

// -------------------------
// Get git branch safely
// -------------------------
void get_git_branch(char *out, int max) {
    FILE *fp = popen("git rev-parse --abbrev-ref HEAD 2>/dev/null", "r");
    if (!fp) {
        snprintf(out, max, "none");
        return;
    }

    if (!fgets(out, max, fp)) {
        snprintf(out, max, "none");
        pclose(fp);
        return;
    }

    pclose(fp);

    out[strcspn(out, "\n")] = 0;
}

// -------------------------
// MAIN
// -------------------------
int main(int argc, char *argv[]) {

    if (argc < 2) {
        printf("JARVIS: missing prompt\n");
        return 1;
    }

    char prompt[JARVIS_MAX_INPUT] = {0};
    char safe_prompt[JARVIS_MAX_INPUT] = {0};
    char json[JSON_SIZE] = {0};

    // -------------------------
    // Build prompt
    // -------------------------
    char *p = prompt;

    for (int i = 1; i < argc; i++) {
        int remaining = JARVIS_MAX_INPUT - (p - prompt) - 1;
        if (remaining <= 0) break;

        int written = snprintf(p, remaining, "%s", argv[i]);
        if (written < 0) break;

        p += written;

        if (i < argc - 1) {
            *p = ' ';
            p++;
        }
    }

    *p = '\0';

    escape_json(safe_prompt, prompt, sizeof(safe_prompt));

    // -------------------------
    // SYSTEM CONTEXT
    // -------------------------
    char cwd[PATH_MAX];
    char git_branch[128] = "none";
    char git_status[64] = "clean";
    char last_cmd[256] = "unknown";
    char dir_list[1024] = "";
    char safe_dir[1024];

    getcwd(cwd, sizeof(cwd));
    get_git_branch(git_branch, sizeof(git_branch));

    // git dirty state
    FILE *gp = popen("git status --porcelain 2>/dev/null | head -1", "r");
    if (gp) {
        char buf[64];
        if (fgets(buf, sizeof(buf), gp)) {
            snprintf(git_status, sizeof(git_status), "dirty");
        }
        pclose(gp);
    }

    // last command
    FILE *hc = popen("fc -ln -1 2>/dev/null", "r");
    if (hc) {
        if (fgets(last_cmd, sizeof(last_cmd), hc)) {
            last_cmd[strcspn(last_cmd, "\n")] = 0;
        }
        pclose(hc);
    }

    // directory snapshot
    FILE *dp = popen("ls -1 2>/dev/null | head -20", "r");
    if (dp) {
        char line[128];
        int len = 0;

        while (fgets(line, sizeof(line), dp)) {
            int l = strlen(line);
            if (len + l >= sizeof(dir_list) - 1) break;

            strcpy(dir_list + len, line);
            len += l;
        }

        pclose(dp);

        if (len > 0 && dir_list[len - 1] == '\n') {
            dir_list[len - 1] = '\0';
        }
    }

    escape_json(safe_dir, dir_list, sizeof(safe_dir));

    char *shell = getenv("SHELL");
    if (!shell) shell = "unknown";

    char *host = getenv("HOSTNAME");
    if (!host) host = "unknown";

    // -------------------------
    // Build JSON
    // -------------------------
    snprintf(json, sizeof(json),
        "{"
            "\"context\":{"
                "\"cwd\":\"%s\","
                "\"git_branch\":\"%s\","
                "\"git_status\":\"%s\","
                "\"last_cmd\":\"%s\","
                "\"dir\":\"%s\","
                "\"shell\":\"%s\","
                "\"host\":\"%s\""
            "},"
            "\"prompt\":\"%s\""
        "}",
        cwd,
        git_branch,
        git_status,
        last_cmd,
        safe_dir,
        shell,
        host,
        safe_prompt
    );

    if (debug == 1) {
      printf("\nJARVIS JSON:\n%s\n\n", json);
    }
    // -------------------------
    // Execute Python
    // -------------------------
    char *args[] = {
        "/home/arvin/.jarvis_env/bin/python",
        "/home/arvin/jarvis_v7/src/cli.py",
        json,
        NULL
    };

    pid_t pid = fork();

    if (pid < 0) {
        perror("fork failed");
        return 1;
    }

    if (pid == 0) {
        execvp(args[0], args);  // FIX: use args[0], not hardcoded string
        perror("execvp failed");
        exit(1);
    }

    wait(NULL);

    return 0;
}