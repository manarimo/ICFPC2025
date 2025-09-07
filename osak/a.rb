require 'json'

obj = JSON.parse(ARGF.read)
matrix = Array.new(6) { Array.new(6, nil) }

obj.each do |conn|
  matrix[conn['from']['room']][conn['from']['door']] = conn['to']['room']
  matrix[conn['to']['room']][conn['to']['door']] = conn['from']['room']
end

matrix.each do |row|
  puts row.join(' ')
end
