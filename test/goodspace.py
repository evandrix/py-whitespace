import sys
USAGE = 'This is just test input for the fixspace script (lotsa bad whitespace)'
def main():

    args = sys.argv[1:]
    if args:
        if args[0] in ('-h', '--help', '-?'):
            print USAGE
        sys.exit(0)

        if '--' in args:
            if True:
                args.remove('--')


if __name__ == '__main__':
    main()
