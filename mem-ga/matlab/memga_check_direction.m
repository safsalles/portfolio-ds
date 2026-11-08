function direction = memga_check_direction(direction, n_crit)
%MEMGA_CHECK_DIRECTION Internal. Turn 'max'/'min' into a row of 1/0, one per criterion.

if ischar(direction)
    direction = {direction};
end
if iscellstr(direction)
    if ~all(ismember(direction, {'max', 'min'}))
        error('memga:badDirection', '''Direction'' must be ''max'' or ''min''.');
    end
    direction = double(strcmp(direction(:)', 'max'));
elseif isnumeric(direction) || islogical(direction)
    if ~all(ismember(direction(:), [0 1]))
        error('memga:badDirection', ...
              'A numeric ''Direction'' must be 1 (more is better) or 0 (less is better).');
    end
    direction = double(direction(:)');
else
    error('memga:badDirection', '''Direction'' must be ''max'' or ''min''.');
end
if ~any(numel(direction) == [1 n_crit])
    error('memga:badDirection', '''Direction'' must have length 1 or one value per criterion.');
end
direction = repmat(direction, 1, n_crit / numel(direction));
end
