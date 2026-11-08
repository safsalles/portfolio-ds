function problem = memga_load_example(name)
%MEMGA_LOAD_EXAMPLE Load one of the fictional examples that ship with the package.
%
%   problem = MEMGA_LOAD_EXAMPLE('small') returns 8 candidates graded on six
%   criteria, to choose 2. Candidates A1 and A2 have the best averages but
%   are alike, while A3 is the opposite.
%
%   problem = MEMGA_LOAD_EXAMPLE('large') returns 300 candidates (150
%   analysts, 90 engineers and 60 managers) graded on eight criteria, to
%   build a team of 4 with the genetic algorithm.
%
%   Example:
%     memga_print(memga(memga_load_example('small'), 2))

if nargin < 1
    name = 'small';
end
folders = struct('small', 'recruiting-small', 'large', 'recruiting-large');
if ~isfield(folders, name)
    error('memga:badExample', 'Unknown example ''%s''. Use ''small'' or ''large''.', name);
end
here = fileparts(mfilename('fullpath'));
problem = memga_read_problem(fullfile(here, 'data', folders.(name)));
end
