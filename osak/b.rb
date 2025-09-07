line = ARGF.read
puts line.scan(/\(.*?\)/).join("\n")
