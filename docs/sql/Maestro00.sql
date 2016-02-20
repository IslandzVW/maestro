delimiter $$

CREATE DATABASE `maestro` /*!40100 DEFAULT CHARACTER SET utf8 */$$

CREATE TABLE `computecontainers` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `hostname` varchar(128) NOT NULL,
  `provided_resource_type` int(11) NOT NULL,
  `provided_resource_count` int(11) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=14 DEFAULT CHARSET=utf8$$

CREATE TABLE `computeresourceauth` (
  `resource_id` int(11) NOT NULL,
  `username_enc` varchar(256) NOT NULL,
  `password_enc` varchar(256) NOT NULL,
  PRIMARY KEY (`resource_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8$$

CREATE TABLE `computeresources` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `type` int(11) NOT NULL,
  `container_id` int(11) NOT NULL,
  `hostname` varchar(128) DEFAULT NULL,
  `internal_ip` varchar(64) DEFAULT NULL,
  `external_ip` varchar(64) DEFAULT NULL,
  `state` int(11) unsigned NOT NULL,
  `flags` int(11) NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `IDX_INTERNAL_IP` (`internal_ip`)
) ENGINE=InnoDB AUTO_INCREMENT=12 DEFAULT CHARSET=utf8$$

CREATE TABLE `computeresourcestatedefs` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `name` varchar(64) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8$$

CREATE TABLE `computeresourcestats` (
  `collected_on` datetime NOT NULL,
  `computeresource_id` int(11) NOT NULL,
  `cpu_used_percentage` float NOT NULL,
  `memory_used_percentage` float NOT NULL,
  `disk_used_percentage` float NOT NULL,
  PRIMARY KEY (`collected_on`,`computeresource_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8$$

CREATE TABLE `computeresourcetypes` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(64) NOT NULL,
  `total_compute_units` int(11) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8$$

CREATE TABLE `deployedregions` (
  `id` char(36) NOT NULL,
  `name` varchar(64) NOT NULL,
  `owner` char(36) NOT NULL,
  `estate_id` char(36) NOT NULL,
  `product_type` int(11) NOT NULL,
  `grid_loc_x` int(11) NOT NULL,
  `grid_loc_y` int(11) NOT NULL,
  `host_resource` int(11) DEFAULT NULL,
  `state` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `IDX_HOST_RESOURCE` (`host_resource`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8$$

CREATE TABLE `deployedregionsstatedefs` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `name` varchar(64) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8$$

CREATE TABLE `deployedregionstats` (
  `collected_on` datetime NOT NULL,
  `region_id` char(36) NOT NULL,
  `cpu_used_percentage` float NOT NULL,
  `memory_used` bigint(20) NOT NULL,
  `thread_count` int(11) NOT NULL,
  `handle_count` int(11) NOT NULL,
  PRIMARY KEY (`collected_on`,`region_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8$$

CREATE TABLE `producttypes` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(64) NOT NULL,
  `compute_units` int(11) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8$$

CREATE TABLE `taskgroups` (
  `id` char(36) NOT NULL,
  `name` varchar(64) DEFAULT NULL,
  `submitted_on` datetime NOT NULL,
  `concurrency_limit` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8$$

CREATE TABLE `tasks` (
  `id` char(36) NOT NULL,
  `friendly_name` varchar(128) NOT NULL,
  `task_group_id` char(36) DEFAULT NULL,
  `status` int(11) NOT NULL,
  `resource_id` int(11) NOT NULL,
  `region_id` char(36) DEFAULT NULL,
  `exclusivity` int(11) NOT NULL DEFAULT '0',
  `tasklet` varchar(64) NOT NULL,
  `parameters` text,
  `submitted_on` datetime NOT NULL,
  `started_on` datetime DEFAULT NULL,
  `progress` int(11) NOT NULL DEFAULT '0',
  `error_info` text,
  `completed_on` datetime DEFAULT NULL,
  `return_value` text,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8$$

