function run_tests(varargin)
%RUN_TESTS Test the MATLAB/Octave version of memga.
%
%   run_tests runs the quick tests. run_tests('full') also runs the genetic
%   algorithm with its default settings on the large example, which takes a
%   few minutes. The reference values in tests/ref come from the Python
%   version, so the ports agree.
%
%   Works in MATLAB and in GNU Octave. Run it from any folder.

full = any(strcmp(varargin, 'full'));
here = fileparts(mfilename('fullpath'));
addpath(fileparts(here));

tests = {@test_problem_checks, @test_read_problem, @test_exhaustive_matches_python, ...
         @test_scores_match_python, @test_example_prefers_complement, @test_quotas_exhaustive, ...
         @test_traditional_and_score, @test_ga_basics, @test_ga_seed, ...
         @test_ga_finds_exhaustive_best, @test_bad_arguments, @test_print_and_radar, ...
         @test_warns_when_no_set_reaches_tau};
if full
    tests{end + 1} = @test_ga_large_best;
end

failed = 0;
for k = 1:numel(tests)
    name = func2str(tests{k});
    try
        tests{k}(here);
        fprintf('ok      %s\n', name);
    catch err
        failed = failed + 1;
        fprintf('FAILED  %s\n        %s\n', name, err.message);
    end
end
fprintf('\n%d tests, %d failed\n', numel(tests), failed);
if failed > 0
    error('memga:testsFailed', '%d tests failed.', failed);
end
end

% ----------------------------------------------------------------------
function check(condition, message)
if ~condition
    error('memga:test', message);
end
end

function check_close(a, b, tolerance, message)
if any(abs(a(:) - b(:)) > tolerance)
    error('memga:test', '%s (got %g, expected %g)', message, a(find(abs(a(:) - b(:)) > tolerance, 1)), ...
          b(find(abs(a(:) - b(:)) > tolerance, 1)));
end
end

function check_error(fn, identifier)
try
    fn();
catch err
    check(strcmp(err.identifier, identifier), ...
          sprintf('expected error %s but got %s: %s', identifier, err.identifier, err.message));
    return
end
error('memga:test', 'expected error %s but nothing happened', identifier);
end

function rows = read_ref(here, name)
% Reads a reference CSV as a cell array of rows, skipping the header.
text = fileread(fullfile(here, 'ref', name));
lines = regexp(text, '\r\n|\n|\r', 'split');
lines = lines(~cellfun(@isempty, lines));
rows = cell(numel(lines) - 1, 1);
for k = 2:numel(lines)
    rows{k - 1} = split_csv(lines{k});
end
end

function fields = split_csv(line)
fields = {};
current = '';
quoted = false;
for k = 1:numel(line)
    c = line(k);
    if c == '"'
        quoted = ~quoted;
    elseif c == ',' && ~quoted
        fields{end + 1} = current; %#ok<AGROW>
        current = '';
    else
        current(end + 1) = c; %#ok<AGROW>
    end
end
fields{end + 1} = current;
end

function quotas = recruiting_quotas()
quotas = struct('analyst', 2, 'engineer', 1, 'manager', 1);
end

% ----------------------------------------------------------------------
function test_problem_checks(~)
good = [1 2; 3 4; 5 7];
check_error(@() memga_problem('a'), 'memga:badValues');
check_error(@() memga_problem([1 NaN; 2 3]), 'memga:badValues');
check_error(@() memga_problem([1 2]), 'memga:badValues');
check_error(@() memga_problem(good, 'Direction', 'up'), 'memga:badDirection');
check_error(@() memga_problem(good, 'Weights', -1), 'memga:badWeights');
check_error(@() memga_problem(good, 'Groups', {'a', 'b'}), 'memga:badGroups');
check_error(@() memga_problem(good, 'Complementarity', zeros(3)), 'memga:badComplementarity');
check_error(@() memga_problem(good, 'Nonsense', 1), 'memga:badOptions');
p = memga_problem(good, 'Direction', {'max', 'min'}, 'Weights', [1 0.5]);
check(isequal(p.direction, [1 0]), 'direction');
check(isequal(p.weights, [1 0.5]), 'weights');
check(isequal(p.alternatives, {'A1', 'A2', 'A3'}), 'default names');
end

function test_read_problem(~)
small = memga_load_example('small');
check(isequal(size(small.values), [8 6]), 'small shape');
check(small.direction(strcmp(small.criteria, 'Absences')) == 0, 'absences direction');
check(isequal(small.complementarity, small.complementarity'), 'symmetric');
large = memga_load_example('large');
check(isequal(size(large.values), [300 8]), 'large shape');
check(isequal(unique(large.groups), {'analyst', 'engineer', 'manager'}), 'groups');
check(sum(strcmp(large.groups, 'analyst')) == 150, 'analysts');
check_error(@() memga_load_example('huge'), 'memga:badExample');
check_error(@() memga_read_problem(tempname), 'memga:fileNotFound');
end

function test_exhaustive_matches_python(here)
small = memga_load_example('small');
cases = {'mean', 'media', 2, 28; 'mean', 'media', 3, 56; 'minimum', 'minimo', 2, 8; 'minimum', 'minimo', 3, 17};
for c = 1:size(cases, 1)
    % With the "minimum" rule, many sets have a pair that is exactly at tau in exact
    % arithmetic. Python let floating point push some below tau and this version
    % rounds them in, so only the top of the ranking is compared for that rule.
    ref = read_ref(here, sprintf('exhaustive_%s_%d.csv', cases{c, 2}, cases{c, 3}));
    result = memga(small, cases{c, 3}, 'Rule', cases{c, 1}, 'Tau', 0.24);
    n_rows = cases{c, 4};
    check(numel(result.ranking.score) == numel(ref), 'number of sets');
    for k = 1:n_rows
        check(result.ranking.position(k) == str2double(ref{k}{1}), ...
              sprintf('%s %d position of row %d', cases{c, 1}, cases{c, 3}, k));
        check(strcmp(result.ranking.set{k}, strrep(ref{k}{2}, ',', ', ')), ...
              sprintf('%s %d set of row %d', cases{c, 1}, cases{c, 3}, k));
        check_close(result.ranking.score(k), str2double(ref{k}{3}), 1e-12, 'score');
    end
end
end

function test_scores_match_python(here)
ref = read_ref(here, 'ratings.csv');
problems = struct('small', memga_load_example('small'), 'large', memga_load_example('large'));
skipped = 0;
for k = 1:numel(ref)
    row = ref{k};
    problem = problems.(row{1});
    rule_name = 'minimum';
    if strcmp(row{2}, 'media')
        rule_name = 'mean';
    end
    tau = str2double(row{3});
    team = sscanf(row{4}, '%d')';
    rule = memga_rules('build', problem, rule_name, tau, numel(team));
    means = mean(rule.payment(team, :), 1);
    % A value that is exactly tau in exact arithmetic can fall on either side of it in
    % floating point, and the languages sum in a different order. Skip those teams.
    if any(abs(memga_rules('values', rule, means) - tau) < 1e-9)
        skipped = skipped + 1;
        continue
    end
    rated = memga_rules('rate', rule, team);
    check_close(rated.score, str2double(row{5}), 1e-12, sprintf('score of row %d', k));
    check_close(rated.tie, str2double(row{6}), 1e-10, sprintf('tie of row %d', k));
end
check(skipped < numel(ref) / 10, 'too many rows skipped');
end

function test_example_prefers_complement(~)
result = memga(memga_load_example('small'), 2);
check_close(result.score, 2 / 3, 1e-12, 'best score');
check(any(strcmp(result.team{1}, {'A1', 'A2'})) && strcmp(result.team{2}, 'A3'), 'best pair');
check(isequal(sort(result.traditional.team), {'A1', 'A2'}), 'traditional choice');
check(result.traditional.score < result.score, 'traditional is worse');
check(isequal(result.ranking.position(1:3)', [1 1 3]), 'ties share a position');
check(~any(diff(result.ranking.score) > 0), 'ranking goes from best to worst');
check(strcmp(memga_ranks_text(result), 'ranks 3'), 'traditional pair ranks 3rd');
end

function text = memga_ranks_text(result)
text = '';
for k = 1:numel(result.ranking.members)
    if isempty(setxor(result.ranking.members{k}, result.traditional.team))
        text = sprintf('ranks %d', result.ranking.position(k));
        return
    end
end
end

function test_quotas_exhaustive(~)
small = memga_load_example('small');
grouped = memga_problem(small.values, 'Alternatives', small.alternatives, 'Criteria', small.criteria, ...
                        'Direction', small.direction, 'Weights', small.weights, ...
                        'Groups', {'p', 'p', 'p', 'q', 'q', 'q', 'q', 'q'}, ...
                        'Complementarity', small.complementarity);
result = memga(grouped, [], 'Quotas', struct('p', 1, 'q', 1), 'Tau', 0.24);
check(numel(result.ranking.score) == 15, 'only valid sets');
for k = 1:numel(result.ranking.members)
    kinds = sort(grouped.groups(ismember(grouped.alternatives, result.ranking.members{k})));
    check(isequal(kinds, {'p', 'q'}), 'one of each group');
end
cellform = memga(grouped, 2, 'Quotas', {'p', 1; 'q', 1}, 'Tau', 0.24);
check(isequal(cellform.team, result.team), 'cell array quotas');
end

function test_traditional_and_score(~)
small = memga_load_example('small');
check(isequal(sort(memga_traditional(small, 2)), {'A1', 'A2'}), 'traditional');
check_close(memga_score(small, {'A1', 'A3'}), 2 / 3, 1e-12, 'score A1 A3');
check(memga_score(small, {'A1', 'A2'}) < memga_score(small, {'A1', 'A3'}), 'A1 A2 scores lower');
check_error(@() memga_score(small, {'A1', 'Z9'}), 'memga:badTeam');
large = memga_load_example('large');
team = memga_traditional(large, [], struct('names', {{'analyst', 'engineer', 'manager'}}, 'counts', [2 1 1]));
groups = sort(large.groups(ismember(large.alternatives, team)));
check(isequal(groups, {'analyst', 'analyst', 'engineer', 'manager'}), 'traditional respects quotas');
end

function test_ga_basics(~)
large = memga_load_example('large');
quick = memga_options('iterations', 200);
result = memga(large, [], 'Method', 'ga', 'Quotas', recruiting_quotas(), 'Options', quick, 'Seed', 1);
groups = sort(large.groups(ismember(large.alternatives, result.team)));
check(isequal(groups, {'analyst', 'analyst', 'engineer', 'manager'}), 'quotas respected');
check(numel(unique(result.team)) == 4, 'no duplicates');
check(numel(result.history) == 200, 'history length');
check(all(diff(result.history) >= 0), 'history never decreases');
check(result.history(end) == result.score, 'history ends at the score');
check(strcmp(result.rule, 'minimum'), 'default rule of the genetic algorithm');
end

function test_ga_seed(~)
large = memga_load_example('large');
quick = memga_options('iterations', 200);
args = {'Method', 'ga', 'Quotas', recruiting_quotas(), 'Options', quick, 'Seed', 4};
first = memga(large, [], args{:});
second = memga(large, [], args{:});
check(isequal(first.team, second.team), 'same seed, same team');
end

function test_ga_finds_exhaustive_best(~)
small = memga_load_example('small');
exhaustive = memga(small, 2, 'Rule', 'minimum');
ga = memga(small, 2, 'Method', 'ga', 'Rule', 'minimum', 'Options', memga_options('iterations', 300), 'Seed', 5);
check_close(ga.score, exhaustive.score, 1e-12, 'genetic algorithm reaches the exhaustive best');
end

function test_bad_arguments(~)
small = memga_load_example('small');
large = memga_load_example('large');
check_error(@() memga(small), 'memga:badSize');
check_error(@() memga(small, 20), 'memga:badSize');
check_error(@() memga(small, 1), 'memga:badSize');
check_error(@() memga(small, 2, 'Method', 'grid'), 'memga:badMethod');
check_error(@() memga(small, 2, 'Rule', 'median'), 'memga:badRule');
check_error(@() memga(small, 2, 'Tau', 0), 'memga:badTau');
check_error(@() memga(small, 2, 'Quotas', struct('a', 2)), 'memga:badQuotas');
check_error(@() memga(large, 3, 'Quotas', recruiting_quotas()), 'memga:badSize');
check_error(@() memga(large, [], 'Quotas', struct('pilot', 2)), 'memga:badQuotas');
check_error(@() memga(large, 4, 'Rule', 'minimum'), 'memga:tooLarge');
check_error(@() memga_options('population', 1), 'memga:badOptions');
check_error(@() memga_options('iterations', 1.5), 'memga:badOptions');
end

function test_print_and_radar(~)
small = memga_load_example('small');
result = memga(small, 2);
text = evalc('memga_print(result)');
check(~isempty(strfind(text, 'A1, A3')), 'print shows the ranking');
check(~isempty(strfind(text, 'Traditional choice')), 'print shows the traditional choice');
set(0, 'DefaultFigureVisible', 'off');
memga_radar(result);
close all
set(0, 'DefaultFigureVisible', 'on');
end

function test_warns_when_no_set_reaches_tau(~)
values = [9 4 3; 8 5 4; 3 9 8; 6 6 6];
tiny = memga_problem(values, 'Direction', {'max', 'max', 'min'});
lastwarn('');
result = memga(tiny, 2, 'Tau', 0.2);
[~, id] = lastwarn;
check(result.score == 0, 'every set scores 0');
check(strcmp(id, 'memga:noSetReachesTau'), 'warns when no set reaches tau');
lastwarn('');
memga(memga_load_example('small'), 2);
[~, id] = lastwarn;
check(~strcmp(id, 'memga:noSetReachesTau'), 'no warning when some set reaches tau');
end

function test_ga_large_best(here)
ref = read_ref(here, 'ga_large.csv');
large = memga_load_example('large');
for k = 1:numel(ref)
    rule_name = 'minimum';
    if strcmp(ref{k}{1}, 'media')
        rule_name = 'mean';
    end
    scores = zeros(1, 3);
    for seed = 1:3
        result = memga(large, [], 'Method', 'ga', 'Rule', rule_name, 'Tau', str2double(ref{k}{2}), ...
                       'Quotas', recruiting_quotas(), 'Seed', seed);
        scores(seed) = result.score;
    end
    check_close(max(scores), str2double(ref{k}{3}), 1e-12, ['best score, rule ' rule_name]);
end
end
