% MEMGA - Multiple Choice Method for selecting sets of alternatives
% Version 1.2.0
%
% Main function
%   memga               - select a set of alternatives (exhaustive search or genetic algorithm)
%
% Define the problem
%   memga_problem       - build a problem from a matrix of values
%   memga_read_problem  - read a problem from CSV files
%   memga_load_example  - load the small or the large fictional example
%
% Results and comparison
%   memga_print         - show a result
%   memga_radar         - radar chart of the selected set
%   memga_score         - score a set that you chose yourself
%   memga_traditional   - the traditional choice, the best ones one by one
%   memga_options       - settings of the genetic algorithm
%
% Tests
%   tests/run_tests     - run the tests (MATLAB or GNU Octave)
