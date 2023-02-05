
import ARAnalysisCompiler
import argparse

epilog = 'Thank you for using the ARAnalysisCompiler ("ARAC") Python Module!'
description = 'Welcome to the ARAnalysisCompiler ("ARAC"), a program to compile patient accounts receivable analysis reports.'


if __name__ == "__main__":

    parser = argparse.ArgumentParser(epilog=epilog, description=description)
    parser.add_argument('-v', '--version', action='version', version='%(prog)s 1.0')
    parser.add_argument('-i', '--input_file', help='Path and filename of the input file downloaded from Crowe', metavar=('[Input file path and name]'), type=str, action='store')
    parser.add_argument('-o', '--output_file', help='Path and filename of the output file downloaded from Crowe.', metavar=('[Output file path and name]'), type=str, action='store')
    args = parser.parse_args()

    if args.input_file:
        input_file = args.input_file
    else:
        raise ValueError('Expected "-i [Input file name and path].')

    if args.output_file:
        output_file = args.output_file
    else:
        raise ValueError('Expected "-o [Output file name and path].')

    compiler = ARAnalysisCompiler.ARAnalysisCompiler()

    compiler.compile(input_file, output_file)


