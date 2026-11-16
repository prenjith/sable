#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#define MAX_LINES 100000
#define MAX_STACK 4096
#define MAX_ENV 4096

typedef struct {
    int type;
    int boolean;
    double num;
    char *str;
} Value;

typedef struct {
    char *name;
    Value value;
} Binding;

static Value stack[MAX_STACK];
static int sp = 0;
static Binding env[MAX_ENV];
static int env_count = 0;

static char *lines[MAX_LINES];
static int nlines = 0;
static char *label_names[MAX_LINES];
static int label_positions[MAX_LINES];
static int label_count = 0;

static void fail(const char *message) {
    fprintf(stderr, "RuntimeError: %s\n", message);
    exit(1);
}

static Value v_nil(void) {
    Value v;
    v.type = 0;
    v.boolean = 0;
    v.num = 0;
    v.str = NULL;
    return v;
}

static Value v_bool(int b) {
    Value v;
    v.type = 1;
    v.boolean = b ? 1 : 0;
    v.num = 0;
    v.str = NULL;
    return v;
}

static Value v_num(double n) {
    Value v;
    v.type = 2;
    v.boolean = 0;
    v.num = n;
    v.str = NULL;
    return v;
}

static Value v_str(const char *s) {
    Value v;
    v.type = 3;
    v.boolean = 0;
    v.num = 0;
    v.str = strdup(s);
    return v;
}

static int truthy(Value v) {
    if (v.type == 0) return 0;
    if (v.type == 1) return v.boolean;
    return 1;
}

static void push(Value v) {
    if (sp >= MAX_STACK) fail("stack overflow");
    stack[sp++] = v;
}

static Value pop(void) {
    if (sp <= 0) fail("stack underflow");
    return stack[--sp];
}

static int env_find(const char *name) {
    for (int i = 0; i < env_count; i++) {
        if (strcmp(env[i].name, name) == 0) return i;
    }
    return -1;
}

static void env_define(const char *name, Value value) {
    int index = env_find(name);
    if (index >= 0) {
        env[index].value = value;
        return;
    }
    if (env_count >= MAX_ENV) fail("too many variables");
    env[env_count].name = strdup(name);
    env[env_count].value = value;
    env_count++;
}

static Value env_load(const char *name) {
    int index = env_find(name);
    if (index < 0) fail("undefined variable");
    return env[index].value;
}

static void env_store(const char *name, Value value) {
    int index = env_find(name);
    if (index < 0) fail("cannot assign to undefined variable");
    env[index].value = value;
}

static void print_value(Value v) {
    if (v.type == 0) {
        printf("nil");
    } else if (v.type == 1) {
        printf("%s", v.boolean ? "true" : "false");
    } else if (v.type == 2) {
        if (v.num == floor(v.num) && fabs(v.num) < 1e16) {
            printf("%lld", (long long)v.num);
        } else {
            printf("%.15g", v.num);
        }
    } else {
        printf("%s", v.str);
    }
}

static Value add(Value a, Value b) {
    if (a.type == 2 && b.type == 2) return v_num(a.num + b.num);
    if (a.type == 3 && b.type == 3) {
        size_t size = strlen(a.str) + strlen(b.str) + 1;
        char *text = malloc(size);
        strcpy(text, a.str);
        strcat(text, b.str);
        Value v;
        v.type = 3;
        v.boolean = 0;
        v.num = 0;
        v.str = text;
        return v;
    }
    fail("cannot add these values");
    return v_nil();
}

static Value subtract(Value a, Value b) {
    if (a.type != 2 || b.type != 2) fail("operator '-' expects numbers");
    return v_num(a.num - b.num);
}

static Value multiply(Value a, Value b) {
    if (a.type != 2 || b.type != 2) fail("operator '*' expects numbers");
    return v_num(a.num * b.num);
}

static Value divide(Value a, Value b) {
    if (a.type != 2 || b.type != 2) fail("operator '/' expects numbers");
    if (b.num == 0) fail("division by zero");
    return v_num(a.num / b.num);
}

static Value modulo(Value a, Value b) {
    if (a.type != 2 || b.type != 2) fail("operator '%' expects numbers");
    if (b.num == 0) fail("division by zero");
    return v_num(fmod(a.num, b.num));
}

static int values_equal(Value a, Value b) {
    if (a.type != b.type) return 0;
    if (a.type == 0) return 1;
    if (a.type == 1) return a.boolean == b.boolean;
    if (a.type == 2) return a.num == b.num;
    return strcmp(a.str, b.str) == 0;
}

static int values_compare(Value a, Value b) {
    if (a.type == 2 && b.type == 2) {
        return (a.num < b.num) ? -1 : (a.num > b.num ? 1 : 0);
    }
    if (a.type == 3 && b.type == 3) {
        return strcmp(a.str, b.str);
    }
    fail("cannot compare these values");
    return 0;
}

static char *parse_string_literal(const char *text) {
    while (*text == ' ') text++;
    if (*text != '"') fail("bad string literal");
    text++;
    size_t capacity = strlen(text) + 1;
    char *out = malloc(capacity);
    size_t length = 0;
    while (*text && *text != '"') {
        if (*text == '\\' && text[1]) {
            text++;
            switch (*text) {
                case 'n': out[length++] = '\n'; break;
                case 't': out[length++] = '\t'; break;
                case 'r': out[length++] = '\r'; break;
                case '\\': out[length++] = '\\'; break;
                case '"': out[length++] = '"'; break;
                default: out[length++] = *text; break;
            }
            text++;
        } else {
            out[length++] = *text++;
        }
    }
    out[length] = '\0';
    return out;
}

static int find_label(const char *name) {
    for (int i = 0; i < label_count; i++) {
        if (strcmp(label_names[i], name) == 0) return label_positions[i];
    }
    fail("unknown label");
    return 0;
}

static void load_program(const char *path) {
    FILE *handle = fopen(path, "r");
    if (!handle) fail("cannot open bytecode file");
    char buffer[4096];
    while (fgets(buffer, sizeof(buffer), handle)) {
        buffer[strcspn(buffer, "\n")] = '\0';
        if (buffer[0] == '\0') continue;
        if (nlines >= MAX_LINES) fail("program too large");
        lines[nlines++] = strdup(buffer);
    }
    fclose(handle);
    for (int i = 0; i < nlines; i++) {
        if (strncmp(lines[i], "LABEL ", 6) == 0) {
            label_names[label_count] = strdup(lines[i] + 6);
            label_positions[label_count] = i;
            label_count++;
        }
    }
}

static void execute(void) {
    int ip = 0;
    while (ip < nlines) {
        char *line = lines[ip];
        if (strncmp(line, "PUSH_NUM ", 9) == 0) {
            push(v_num(atof(line + 9)));
            ip++;
        } else if (strncmp(line, "PUSH_STR ", 9) == 0) {
            push(v_str(parse_string_literal(line + 9)));
            ip++;
        } else if (strcmp(line, "PUSH_NIL") == 0) {
            push(v_nil());
            ip++;
        } else if (strcmp(line, "PUSH_TRUE") == 0) {
            push(v_bool(1));
            ip++;
        } else if (strcmp(line, "PUSH_FALSE") == 0) {
            push(v_bool(0));
            ip++;
        } else if (strncmp(line, "LOAD ", 5) == 0) {
            char name[256];
            sscanf(line + 5, "%255s", name);
            push(env_load(name));
            ip++;
        } else if (strncmp(line, "STORE ", 6) == 0) {
            char name[256];
            sscanf(line + 6, "%255s", name);
            Value assigned = pop();
            env_store(name, assigned);
            push(assigned);
            ip++;
        } else if (strncmp(line, "DEFINE ", 7) == 0) {
            char name[256];
            sscanf(line + 7, "%255s", name);
            env_define(name, pop());
            ip++;
        } else if (strcmp(line, "POP") == 0) {
            pop();
            ip++;
        } else if (strcmp(line, "ADD") == 0) {
            Value b = pop(), a = pop();
            push(add(a, b));
            ip++;
        } else if (strcmp(line, "SUB") == 0) {
            Value b = pop(), a = pop();
            push(subtract(a, b));
            ip++;
        } else if (strcmp(line, "MUL") == 0) {
            Value b = pop(), a = pop();
            push(multiply(a, b));
            ip++;
        } else if (strcmp(line, "DIV") == 0) {
            Value b = pop(), a = pop();
            push(divide(a, b));
            ip++;
        } else if (strcmp(line, "MOD") == 0) {
            Value b = pop(), a = pop();
            push(modulo(a, b));
            ip++;
        } else if (strcmp(line, "NEG") == 0) {
            Value a = pop();
            if (a.type != 2) fail("unary '-' expects a number");
            push(v_num(-a.num));
            ip++;
        } else if (strcmp(line, "NOT") == 0) {
            Value a = pop();
            push(v_bool(!truthy(a)));
            ip++;
        } else if (strcmp(line, "EQ") == 0) {
            Value b = pop(), a = pop();
            push(v_bool(values_equal(a, b)));
            ip++;
        } else if (strcmp(line, "NE") == 0) {
            Value b = pop(), a = pop();
            push(v_bool(!values_equal(a, b)));
            ip++;
        } else if (strcmp(line, "LT") == 0) {
            Value b = pop(), a = pop();
            push(v_bool(values_compare(a, b) < 0));
            ip++;
        } else if (strcmp(line, "LE") == 0) {
            Value b = pop(), a = pop();
            push(v_bool(values_compare(a, b) <= 0));
            ip++;
        } else if (strcmp(line, "GT") == 0) {
            Value b = pop(), a = pop();
            push(v_bool(values_compare(a, b) > 0));
            ip++;
        } else if (strcmp(line, "GE") == 0) {
            Value b = pop(), a = pop();
            push(v_bool(values_compare(a, b) >= 0));
            ip++;
        } else if (strncmp(line, "JUMP ", 5) == 0) {
            char name[256];
            sscanf(line + 5, "%255s", name);
            ip = find_label(name);
        } else if (strncmp(line, "JUMP_IF_FALSE ", 14) == 0) {
            char name[256];
            sscanf(line + 14, "%255s", name);
            if (!truthy(pop())) ip = find_label(name);
            else ip++;
        } else if (strncmp(line, "JUMP_IF_TRUE ", 13) == 0) {
            char name[256];
            sscanf(line + 13, "%255s", name);
            if (truthy(pop())) ip = find_label(name);
            else ip++;
        } else if (strncmp(line, "PRINT ", 6) == 0) {
            int count = atoi(line + 6);
            Value *values = malloc(sizeof(Value) * (count > 0 ? count : 1));
            for (int i = count - 1; i >= 0; i--) values[i] = pop();
            for (int i = 0; i < count; i++) {
                if (i > 0) printf(" ");
                print_value(values[i]);
            }
            printf("\n");
            free(values);
            ip++;
        } else if (strncmp(line, "LABEL ", 6) == 0) {
            ip++;
        } else if (strcmp(line, "HALT") == 0) {
            break;
        } else {
            fail("unknown instruction");
        }
    }
}

int main(int argc, char **argv) {
    if (argc < 2) {
        fprintf(stderr, "usage: sable-vm program.sasm\n");
        return 1;
    }
    load_program(argv[1]);
    execute();
    return 0;
}
