pin = 2.54;
midi_port_w = 19.7;
midi_port_slot_th = 1.2;
midi_port_slot_w = 1;
midi_port_slot_slop = 0.2;
midi_port_wall_w = 7;
midi_port_wall_th = 5;
midi_port_top_pin_offset = 2.7;
midi_port_screw_x = midi_port_w / 2 + midi_port_wall_w / 2;
midi_port_screw_y = midi_port_w / 4;
midi_plug_outer_d = 16.7;
midi_plug_inner_d = 13.2;
midi_plug_slop = 1;
midi_plug_hole_taper = 0.8;
plate_stem_d = 5;
plate_stem_h = 4;
plate_stem_slop = 0.1;
screw_inside_d = 2.5;
screw_outside_d = 3.3;
screw_head_d = 4.8;

module mirror_copy (d) {
    children();
    mirror(d) children();
}

module screw_hole (depth=5, taper=true) {
    taper_h = 1;
    taper_w = screw_head_d - screw_outside_d;
    cylinder(d=screw_inside_d, h=depth * 2, center=true, $fn=50);
    cube([screw_outside_d, 1, depth * 2], center=true);
    cube([1, screw_outside_d, depth * 2], center=true);
    if (taper) {
        cylinder(d1=screw_head_d + taper_w, d2=screw_head_d - taper_w,  h=taper_h * 2, center=true, $fn=50);
    }
}

module midi_port_holder () {
    w_with_wall = midi_port_w + midi_port_wall_w * 2;

    difference () {
        union () {
            difference () {
                union () {
                    translate([0, 0, -(midi_port_slot_th + midi_port_wall_th) / 2])
                        cube([w_with_wall, midi_port_w + midi_port_slot_slop, midi_port_slot_th + midi_port_wall_th], center=true);

                    translate([0, -midi_port_w / 2 + 7, -(midi_port_slot_th + midi_port_wall_th * 2) / 2])
                        cube([w_with_wall, 14, midi_port_slot_th + midi_port_wall_th * 2], center=true);

                }

                translate([0, 0, -midi_port_slot_th / 2])
                    cube([
                        midi_port_w + midi_port_slot_slop * 2,
                        50,
                        midi_port_slot_th + midi_port_slot_slop * 2
                    ], center=true);

                cube([midi_port_w - midi_port_slot_w * 2 + midi_port_slot_slop * 2, 50, 50], center=true);
            }

            translate([
                0,
                midi_port_w / 2 + midi_port_wall_w / 2,
                -(midi_port_slot_th + midi_port_wall_th) / 2
            ])
                cube([
                    w_with_wall,
                    midi_port_wall_w,
                    midi_port_slot_th + midi_port_wall_th
                ], center=true);
        }

        mirror_copy([1, 0, 0])
            translate([
                -pin * 5,
                -midi_port_w / 2,
                -midi_port_top_pin_offset - pin * 2
            ])
                rotate([-90, 0, 0]) screw_hole(taper=false);

        midi_port_holder_stems_placement () {
            plate_stem_negative_insert();
        }
    }
}

module plate_stem () {
    difference () {
        translate([0, 0, -plate_stem_h/2])
            cylinder(d=plate_stem_d, h=plate_stem_h, center=true, $fn=50);

        translate([0, 0, -plate_stem_h/2])
            rotate([180, 0, 0])
            screw_hole(taper=false);
    }
}

module plate_stem_negative_insert () {
    holding_layer_th = 2;

    // screw-diameter through
    cylinder(d=screw_outside_d, h=50, center=true, $fn=20);

    translate([0, 0, -plate_stem_h / 2])
        cylinder(d=plate_stem_d + plate_stem_slop, h=plate_stem_h + plate_stem_slop, center=true, $fn=50);

    x = 50;
    translate([0, 0, -plate_stem_h - holding_layer_th - x/2])
        cylinder(d=screw_head_d + plate_stem_slop, h=x, center=true, $fn=50);

}

module midi_port_holder_stems_placement () {
    translate([0, 3, 0]) mirror_copy([0, 1, 0]) mirror_copy([1, 0, 0]) {
        translate([midi_port_screw_x, midi_port_screw_y, 0])
        children();
    }
}

module midi_test_plate () {
    th = 5;
    difference () {
        translate([0, 0, th / 2])
            cube([50, 50, th], center=true);

        x = 20;
        cylinder(
            d1=midi_plug_outer_d + midi_plug_slop * 2 - x * midi_plug_hole_taper,
            d2=midi_plug_outer_d + midi_plug_slop * 2 + x * midi_plug_hole_taper,
            h=x,
            center=true,
            $fn=100
        );
    }

    midi_port_holder_stems_placement() {
        plate_stem();
    }
}


midi_test_plate();

!translate([0, 0, -3]) midi_port_holder();
