import sys
from htmltreediff import html_changes

def main(argv=None):
    if not argv:
        argv = sys.argv
    with open(argv[1]) as file_a:
        html_a = file_a.read()
    with open(argv[2]) as file_b:
        html_b = file_b.read()
    print html_changes(html_a, html_b, cutoff=0.0, pretty=True)

if __name__ == '__main__':
    main() # pragma: no cover
