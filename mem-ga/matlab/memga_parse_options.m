function options = memga_parse_options(options, args)
%MEMGA_PARSE_OPTIONS Internal. Fill a struct of defaults from name-value pairs.
%   Names are matched without regard to case. An unknown name is an error.

if mod(numel(args), 2) ~= 0
    error('memga:badOptions', 'Options must come as name-value pairs.');
end
known = fieldnames(options);
for k = 1:2:numel(args)
    name = args{k};
    if ~ischar(name)
        error('memga:badOptions', 'Option names must be text.');
    end
    hit = find(strcmpi(name, known), 1);
    if isempty(hit)
        error('memga:badOptions', 'Unknown option ''%s''.', name);
    end
    options.(known{hit}) = args{k + 1};
end
end
