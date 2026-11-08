function problem = memga_read_problem(folder)
%MEMGA_READ_PROBLEM Read a problem from CSV files.
%
%   problem = MEMGA_READ_PROBLEM(folder) reads criteria.csv,
%   alternatives.csv and, when it exists, complementarity.csv.
%
%   criteria.csv         columns criterion, direction (1 when more is better
%                        and 0 when less is better) and weight.
%   alternatives.csv     column alternative, one column per criterion and,
%                        optionally, a group column.
%   complementarity.csv  column criterion and one column per criterion. The
%                        diagonal is ignored.
%
%   Example:
%     p = memga_read_problem(fullfile(fileparts(which('memga')), 'data', 'recruiting-small'));

criteria_rows = read_table(fullfile(folder, 'criteria.csv'), {'criterion', 'direction', 'weight'});
criteria = criteria_rows.data(:, column(criteria_rows, 'criterion'))';
direction = str2double(criteria_rows.data(:, column(criteria_rows, 'direction')))';
weights = str2double(criteria_rows.data(:, column(criteria_rows, 'weight')))';

alt = read_table(fullfile(folder, 'alternatives.csv'), [{'alternative'}, criteria]);
alternatives = alt.data(:, column(alt, 'alternative'))';
values = zeros(numel(alternatives), numel(criteria));
for j = 1:numel(criteria)
    values(:, j) = str2double(alt.data(:, column(alt, criteria{j})));
end
groups = {};
if any(strcmp(alt.header, 'group'))
    groups = alt.data(:, column(alt, 'group'))';
end

complementarity = [];
path = fullfile(folder, 'complementarity.csv');
if exist(path, 'file')
    matrix_rows = read_table(path, [{'criterion'}, criteria]);
    names = matrix_rows.data(:, column(matrix_rows, 'criterion'))';
    complementarity = zeros(numel(criteria));
    for i = 1:numel(criteria)
        row = find(strcmp(names, criteria{i}), 1);
        for j = 1:numel(criteria)
            if i ~= j
                complementarity(i, j) = str2double(matrix_rows.data{row, column(matrix_rows, criteria{j})});
            end
        end
    end
end

problem = memga_problem(values, 'Alternatives', alternatives, 'Criteria', criteria, ...
                        'Direction', direction, 'Weights', weights, ...
                        'Groups', groups, 'Complementarity', complementarity);
end

function index = column(table_, name)
index = find(strcmp(table_.header, name), 1);
end

function table_ = read_table(path, required)
% A small CSV reader that works in MATLAB and Octave: quotes, comma, header row.
if ~exist(path, 'file')
    error('memga:fileNotFound', 'File not found: %s', path);
end
fid = fopen(path, 'r', 'n', 'UTF-8');
text = fread(fid, Inf, '*char')';
fclose(fid);
if ~isempty(text) && double(text(1)) == 65279   % byte order mark
    text = text(2:end);
end
lines = regexp(text, '\r\n|\n|\r', 'split');
lines = lines(~cellfun(@(line) isempty(strtrim(line)), lines));
header = split_line(lines{1});
missing = setdiff(required, header);
if ~isempty(missing)
    [~, name] = fileparts(path);
    error('memga:missingColumns', 'Missing columns in %s.csv: %s', name, strjoin(missing, ', '));
end
data = cell(numel(lines) - 1, numel(header));
for k = 2:numel(lines)
    fields = split_line(lines{k});
    fields(end + 1:numel(header)) = {''};
    data(k - 1, :) = fields(1:numel(header));
end
table_ = struct('header', {header}, 'data', {data});
end

function fields = split_line(line)
fields = {};
current = '';
quoted = false;
for k = 1:numel(line)
    c = line(k);
    if c == '"'
        quoted = ~quoted;
    elseif c == ',' && ~quoted
        fields{end + 1} = strtrim(current); %#ok<AGROW>
        current = '';
    else
        current(end + 1) = c; %#ok<AGROW>
    end
end
fields{end + 1} = strtrim(current);
end
